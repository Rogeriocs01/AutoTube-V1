import sqlite3
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from core import database
from core.repositorio import salvar_conteudo, salvar_metadados, salvar_projeto
from core.repositorio_publicacao import (
    atualizar_item_fila,
    atualizar_publicacao,
    listar_publicacoes,
    obter_item_fila,
    obter_publicacao,
)
from core import repositorio_publicacao
from core.resultado_publicacao import ResultadoPublicacao
from core.servico_publicacao_db import ServicoPublicacaoDB
from core.interface_autotube import InterfaceAutoTube
from core.pipeline import processar_publicacao


class BancoTemporarioMixin:
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "autotube-test.db"
        self.pasta_original = database.PASTA_AUTOTUBE_DATA
        self.arquivo_original = database.ARQUIVO_BANCO
        database.PASTA_AUTOTUBE_DATA = Path(self.temp_dir.name)
        database.ARQUIVO_BANCO = self.db_path
        self.addCleanup(self._restaurar_banco)
        database.criar_schema()
        self.servico = ServicoPublicacaoDB()
        self._criar_conteudo()

    def _restaurar_banco(self):
        database.PASTA_AUTOTUBE_DATA = self.pasta_original
        database.ARQUIVO_BANCO = self.arquivo_original

    def _criar_conteudo(self, conteudo_id="conteudo-1"):
        salvar_projeto("projeto-1", "Projeto de teste")
        salvar_conteudo(
            conteudo_id=conteudo_id,
            projeto_id="projeto-1",
            id_legado="YT_0001",
            tipo="LONGO",
            nome_arquivo="video.mp4",
            drive_file_id="drive-file-1",
        )
        salvar_metadados(
            conteudo_id=conteudo_id,
            titulo="Título de teste",
            descricao="Descrição",
        )

    def _criar_solicitacao(self, **kwargs):
        parametros = {
            "conteudo_id": "conteudo-1",
            "privacidade": "private",
            "canal_id": "UC1234567890",
        }
        parametros.update(kwargs)
        return self.servico.criar_solicitacao(**parametros)


class ConcorrenciaEIdempotenciaTests(BancoTemporarioMixin, unittest.TestCase):
    def test_solicitacoes_concorrentes_criam_uma_unica_publicacao(self):
        barreira = threading.Barrier(2)
        resultados = []
        erros = []

        def solicitar():
            try:
                barreira.wait(timeout=2)
                resultados.append(self._criar_solicitacao())
            except Exception as erro:
                erros.append(erro)

        threads = [threading.Thread(target=solicitar) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        publicacoes = listar_publicacoes(
            conteudo_id="conteudo-1",
            plataforma="YOUTUBE",
        )
        self.assertEqual(1, len(publicacoes))
        self.assertEqual(1, len(resultados))
        self.assertEqual(1, len(erros))
        self.assertIsInstance(erros[0], RuntimeError)

    def test_apenas_uma_execucao_concorrente_chega_ao_pipeline(self):
        solicitacao = self._criar_solicitacao()
        publicacao_id = solicitacao["publicacao_id"]
        primeira_entrou = threading.Event()
        liberar_primeira = threading.Event()
        chamadas = []
        erros_primeira = []

        def pipeline_simulado(**kwargs):
            chamadas.append(kwargs["video_id"])
            if len(chamadas) == 1:
                primeira_entrou.set()
                liberar_primeira.wait(timeout=5)
            return ResultadoPublicacao.falha(
                mensagem="falha comprovadamente anterior ao upload",
                video_id=kwargs["video_id"],
                etapa="preparacao",
            )

        def executar_primeira():
            try:
                self.servico.executar_publicacao(publicacao_id)
            except Exception as erro:
                erros_primeira.append(erro)

        with patch(
            "core.servico_publicacao_db.processar_publicacao",
            side_effect=pipeline_simulado,
        ):
            thread = threading.Thread(target=executar_primeira)
            thread.start()
            self.assertTrue(primeira_entrou.wait(timeout=3))
            with self.assertRaisesRegex(RuntimeError, "processamento|PROCESSANDO"):
                self.servico.executar_publicacao(publicacao_id)
            liberar_primeira.set()
            thread.join(timeout=5)

        self.assertFalse(erros_primeira)
        self.assertEqual(1, len(chamadas))
        fila = obter_item_fila(publicacao_id)
        self.assertEqual(1, fila["tentativas"])

    def test_external_id_bloqueia_execucao_mesmo_com_status_erro(self):
        solicitacao = self._criar_solicitacao()
        publicacao_id = solicitacao["publicacao_id"]
        atualizar_publicacao(
            publicacao_id,
            status="ERRO",
            external_id="youtube-ja-enviado",
        )
        atualizar_item_fila(publicacao_id, status="ERRO")

        with patch(
            "core.servico_publicacao_db.processar_publicacao"
        ) as pipeline:
            with self.assertRaisesRegex(RuntimeError, "external_id|upload"):
                self.servico.executar_publicacao(publicacao_id)

        pipeline.assert_not_called()

    def test_jobs_distintos_do_mesmo_conteudo_nao_executam_em_paralelo(self):
        primeiro_id = self._criar_solicitacao()["publicacao_id"]
        atualizar_publicacao(primeiro_id, status="ERRO")
        atualizar_item_fila(primeiro_id, status="ERRO")
        segundo_id = self._criar_solicitacao()["publicacao_id"]
        primeira_entrou = threading.Event()
        liberar_primeira = threading.Event()

        def pipeline_simulado(**kwargs):
            primeira_entrou.set()
            liberar_primeira.wait(timeout=5)
            return ResultadoPublicacao.falha(
                mensagem="falha anterior ao upload",
                video_id=kwargs["video_id"],
                etapa="preparacao",
            )

        with patch(
            "core.servico_publicacao_db.processar_publicacao",
            side_effect=pipeline_simulado,
        ) as pipeline:
            thread = threading.Thread(
                target=self.servico.executar_publicacao,
                args=(primeiro_id,),
            )
            thread.start()
            self.assertTrue(primeira_entrou.wait(timeout=3))
            with self.assertRaisesRegex(RuntimeError, "conteúdo|plataforma"):
                self.servico.executar_publicacao(segundo_id)
            liberar_primeira.set()
            thread.join(timeout=5)

        self.assertEqual(1, pipeline.call_count)


class FalhasEAtomicidadeTests(BancoTemporarioMixin, unittest.TestCase):
    def test_falha_apos_upload_preserva_external_id_e_vira_parcial(self):
        publicacao_id = self._criar_solicitacao()["publicacao_id"]

        def falhar_apos_upload(**kwargs):
            callback = kwargs["callback_etapa"]
            callback("UPLOAD", "PROCESSANDO")
            callback(
                "UPLOAD",
                "CONCLUIDO",
                dados={"youtube_id": "youtube-confirmado"},
            )
            raise RuntimeError("falha de persistência posterior")

        with patch(
            "core.servico_publicacao_db.processar_publicacao",
            side_effect=falhar_apos_upload,
        ):
            resultado = self.servico.executar_publicacao(publicacao_id)

        publicacao = obter_publicacao(publicacao_id)
        fila = obter_item_fila(publicacao_id)
        self.assertFalse(resultado.sucesso)
        self.assertEqual("youtube-confirmado", resultado.youtube_id)
        self.assertEqual("youtube-confirmado", publicacao["external_id"])
        self.assertEqual("PARCIAL", publicacao["status"])
        self.assertEqual("PARCIAL", fila["status"])

    def test_resultado_incerto_exige_reconciliacao_e_bloqueia_retry(self):
        publicacao_id = self._criar_solicitacao()["publicacao_id"]

        def resultado_incerto(**kwargs):
            kwargs["callback_etapa"]("UPLOAD", "PROCESSANDO")
            raise RuntimeError("conexão perdida durante upload")

        with patch(
            "core.servico_publicacao_db.processar_publicacao",
            side_effect=resultado_incerto,
        ):
            resultado = self.servico.executar_publicacao(publicacao_id)

        self.assertFalse(resultado.sucesso)
        self.assertEqual("RECONCILIACAO", obter_publicacao(publicacao_id)["status"])
        self.assertEqual("RECONCILIACAO", obter_item_fila(publicacao_id)["status"])

        with patch(
            "core.servico_publicacao_db.processar_publicacao"
        ) as pipeline:
            with self.assertRaisesRegex(RuntimeError, "RECONCILIACAO"):
                self.servico.executar_publicacao(publicacao_id)
        pipeline.assert_not_called()

    def test_falha_anterior_ao_upload_permite_retry_controlado(self):
        publicacao_id = self._criar_solicitacao()["publicacao_id"]
        falha = ResultadoPublicacao.falha(
            mensagem="arquivo não preparado",
            video_id="YT_0001",
            etapa="download_video",
        )

        with patch(
            "core.servico_publicacao_db.processar_publicacao",
            return_value=falha,
        ) as pipeline:
            self.servico.executar_publicacao(publicacao_id)
            self.servico.executar_publicacao(publicacao_id)

        self.assertEqual(2, pipeline.call_count)
        self.assertEqual("ERRO", obter_publicacao(publicacao_id)["status"])
        self.assertEqual(2, obter_item_fila(publicacao_id)["tentativas"])

    def test_falha_intermediaria_reverte_criacao_completa(self):
        etapas_invalidas = repositorio_publicacao.ETAPAS_YOUTUBE + (
            ("UPLOAD", True),
        )

        with patch.object(
            repositorio_publicacao,
            "ETAPAS_YOUTUBE",
            etapas_invalidas,
        ):
            with self.assertRaises(sqlite3.IntegrityError):
                self._criar_solicitacao()

        self.assertEqual([], listar_publicacoes(conteudo_id="conteudo-1"))

    def test_evento_de_upload_e_external_id_sao_atomicos(self):
        publicacao_id = self._criar_solicitacao()["publicacao_id"]
        self.servico.registrar_evento_etapa(
            publicacao_id,
            "UPLOAD",
            "PROCESSANDO",
        )
        conexao = database.conectar_banco()
        try:
            conexao.execute(
                """
                CREATE TRIGGER falhar_historico_upload
                BEFORE INSERT ON historico_publicacao
                WHEN NEW.etapa = 'UPLOAD' AND NEW.status = 'CONCLUIDO'
                BEGIN
                    SELECT RAISE(ABORT, 'falha simulada');
                END;
                """
            )
            conexao.commit()
        finally:
            conexao.close()

        with self.assertRaises(sqlite3.IntegrityError):
            self.servico.registrar_evento_etapa(
                publicacao_id,
                "UPLOAD",
                "CONCLUIDO",
                dados={"youtube_id": "youtube-confirmado"},
            )

        publicacao = obter_publicacao(publicacao_id)
        upload = next(
            etapa
            for etapa in repositorio_publicacao.listar_etapas(publicacao_id)
            if etapa["etapa"] == "UPLOAD"
        )
        self.assertIsNone(publicacao["external_id"])
        self.assertEqual("PROCESSANDO", upload["status"])

    def test_falha_no_historico_reverte_finalizacao(self):
        publicacao_id = self._criar_solicitacao()["publicacao_id"]
        repositorio_publicacao.adquirir_execucao(publicacao_id)
        conexao = database.conectar_banco()
        try:
            conexao.execute(
                """
                CREATE TRIGGER falhar_historico_final
                BEFORE INSERT ON historico_publicacao
                WHEN NEW.etapa = 'FINALIZACAO'
                     AND NEW.status = 'CONCLUIDO'
                BEGIN
                    SELECT RAISE(ABORT, 'falha simulada');
                END;
                """
            )
            conexao.commit()
        finally:
            conexao.close()

        resultado = ResultadoPublicacao.sucesso_publicacao(
            video_id="YT_0001",
            youtube_id="youtube-confirmado",
            playlist_ok=True,
            thumbnail_ok=True,
            drive_ok=True,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.servico.finalizar_sucesso(publicacao_id, resultado)

        self.assertEqual("PROCESSANDO", obter_publicacao(publicacao_id)["status"])
        self.assertEqual("PROCESSANDO", obter_item_fila(publicacao_id)["status"])


class ValidacoesOperacionaisTests(BancoTemporarioMixin, unittest.TestCase):
    def test_agendamento_futuro_nao_chega_ao_pipeline(self):
        futuro = (datetime.now() + timedelta(hours=1)).isoformat()
        publicacao_id = self._criar_solicitacao(
            agendado_para=futuro
        )["publicacao_id"]

        with patch(
            "core.servico_publicacao_db.processar_publicacao"
        ) as pipeline:
            with self.assertRaisesRegex(RuntimeError, "agendado|futuro"):
                self.servico.executar_publicacao(publicacao_id)

        pipeline.assert_not_called()
        self.assertEqual("AGUARDANDO", obter_publicacao(publicacao_id)["status"])
        self.assertEqual(0, obter_item_fila(publicacao_id)["tentativas"])
        self.assertIsNone(self.servico.consultar_proximo_job())

    def test_canal_solicitado_divergente_bloqueia_antes_de_download(self):
        video = {
            "arquivo": "video.mp4",
            "drive_id": "drive-file-1",
            "tipo_conteudo": "LONGO",
            "status": "PENDENTE",
        }
        metadados = {"titulo": "Título", "descricao": "Descrição"}

        with (
            patch("core.pipeline.obter_projeto_ativo", return_value={"nome": "P"}),
            patch("core.pipeline.validar_canal_youtube", return_value=True),
            patch(
                "core.pipeline.obter_canal_youtube_autenticado",
                return_value={"id": "UC-AUTENTICADO", "nome": "Canal"},
            ),
            patch("core.pipeline.baixar_thumbnail") as baixar_thumbnail_mock,
            patch("core.pipeline.baixar_video") as baixar_video_mock,
            patch("core.pipeline.publicar_video") as publicar_mock,
        ):
            resultado = processar_publicacao(
                video_id="YT_0001",
                video=video,
                privacidade="private",
                pedir_confirmacao=False,
                metadados_override=metadados,
                canal_id_solicitado="UC-SOLICITADO",
            )

        self.assertFalse(resultado.sucesso)
        self.assertEqual("canal_divergente", resultado.etapa)
        baixar_thumbnail_mock.assert_not_called()
        baixar_video_mock.assert_not_called()
        publicar_mock.assert_not_called()

    def test_parametros_operacionais_invalidos_sao_rejeitados(self):
        casos = (
            {"privacidade": "friends"},
            {"prioridade": -1},
            {"prioridade": "alta"},
            {"canal_id": "   "},
        )

        for parametros in casos:
            with self.subTest(parametros=parametros):
                with self.assertRaises(ValueError):
                    self._criar_solicitacao(**parametros)

    def test_falha_de_upload_remove_video_e_thumbnail_temporarios(self):
        video_path = Path(self.temp_dir.name) / "video.mp4"
        thumb_path = Path(self.temp_dir.name) / "thumb.jpg"
        video_path.write_bytes(b"video")
        thumb_path.write_bytes(b"thumb")
        video = {
            "arquivo": "video.mp4",
            "drive_id": "drive-file-1",
            "tipo_conteudo": "LONGO",
            "status": "PENDENTE",
        }
        metadados = {"titulo": "Título", "descricao": "Descrição"}

        with (
            patch("core.pipeline.obter_projeto_ativo", return_value={"nome": "P"}),
            patch("core.pipeline.validar_canal_youtube", return_value=True),
            patch(
                "core.pipeline.obter_canal_youtube_autenticado",
                return_value={"id": "UC-CANAL", "nome": "Canal"},
            ),
            patch("core.pipeline.baixar_thumbnail", return_value=thumb_path),
            patch("core.pipeline.baixar_video", return_value=video_path),
            patch("core.pipeline.publicar_video", return_value=None),
        ):
            resultado = processar_publicacao(
                video_id="YT_0001",
                video=video,
                privacidade="private",
                pedir_confirmacao=False,
                metadados_override=metadados,
                canal_id_solicitado="UC-CANAL",
            )

        self.assertFalse(resultado.sucesso)
        self.assertFalse(video_path.exists())
        self.assertFalse(thumb_path.exists())

    def test_excecao_pos_upload_remove_arquivos_temporarios(self):
        video_path = Path(self.temp_dir.name) / "video-excecao.mp4"
        thumb_path = Path(self.temp_dir.name) / "thumb-excecao.jpg"
        video_path.write_bytes(b"video")
        thumb_path.write_bytes(b"thumb")
        video = {
            "arquivo": "video.mp4",
            "drive_id": "drive-file-1",
            "tipo_conteudo": "LONGO",
            "status": "PENDENTE",
        }
        metadados = {
            "titulo": "Título",
            "descricao": "Descrição",
            "playlist_id": "playlist-1",
        }

        with (
            patch("core.pipeline.obter_projeto_ativo", return_value={"nome": "P"}),
            patch("core.pipeline.validar_canal_youtube", return_value=True),
            patch(
                "core.pipeline.obter_canal_youtube_autenticado",
                return_value={"id": "UC-CANAL", "nome": "Canal"},
            ),
            patch("core.pipeline.baixar_thumbnail", return_value=thumb_path),
            patch("core.pipeline.baixar_video", return_value=video_path),
            patch("core.pipeline.publicar_video", return_value="youtube-id"),
            patch(
                "core.pipeline.adicionar_video_playlist",
                side_effect=RuntimeError("falha simulada"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                processar_publicacao(
                    video_id="YT_0001",
                    video=video,
                    privacidade="private",
                    pedir_confirmacao=False,
                    metadados_override=metadados,
                    canal_id_solicitado="UC-CANAL",
                )

        self.assertFalse(video_path.exists())
        self.assertFalse(thumb_path.exists())

    def test_interface_preserva_chamada_cli_sem_novos_argumentos(self):
        class ServicoFalso:
            def criar_solicitacao(self, **kwargs):
                return kwargs

        resultado = InterfaceAutoTube(ServicoFalso()).solicitar_publicacao(
            "conteudo-1"
        )

        self.assertEqual("conteudo-1", resultado["conteudo_id"])
        self.assertEqual("private", resultado["privacidade"])
        self.assertEqual("YOUTUBE", resultado["plataforma"])


if __name__ == "__main__":
    unittest.main()
