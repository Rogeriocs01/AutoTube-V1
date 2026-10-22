import sqlite3
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from core import database
from core import repositorio_publicacao
from core.autorizacao_publicacao import EmissorAutorizacaoSupervisionada
from core.interface_autotube import InterfaceAutoTube
from core.repositorio import salvar_conteudo, salvar_metadados, salvar_projeto
from core.servico_publicacao_db import ServicoPublicacaoDB


class RelogioControlado:
    def __init__(self):
        self.agora = datetime(2030, 1, 2, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.agora

    def avancar(self, segundos):
        self.agora += timedelta(seconds=segundos)


class AutorizacaoSupervisionadaTests(unittest.TestCase):
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
        salvar_projeto("projeto-1", "Projeto de teste")
        salvar_conteudo(
            conteudo_id="conteudo-1",
            projeto_id="projeto-1",
            id_legado="YT_0001",
            tipo="LONGO",
            nome_arquivo="video.mp4",
            drive_file_id="drive-file-1",
        )
        salvar_metadados(
            conteudo_id="conteudo-1",
            titulo="Título de teste",
            descricao="Descrição",
        )
        self.relogio = RelogioControlado()
        self.emissor = EmissorAutorizacaoSupervisionada(
            emissor_id="emissor-teste",
            relogio=self.relogio,
            validade_maxima_segundos=300,
        )
        self.contexto_operador = self.emissor.criar_contexto_operador(
            "operador-confiavel"
        )
        self.servico = ServicoPublicacaoDB(
            emissor_autorizacao=self.emissor
        )
        self.interface = InterfaceAutoTube(self.servico)

    def _restaurar_banco(self):
        database.PASTA_AUTOTUBE_DATA = self.pasta_original
        database.ARQUIVO_BANCO = self.arquivo_original

    def _parametros(self, **sobrescritas):
        parametros = {
            "conteudo_id": "conteudo-1",
            "privacidade": "private",
            "canal_id": "UC1234567890",
            "prioridade": 100,
            "plataforma": "YOUTUBE",
            "agendado_para": None,
        }
        parametros.update(sobrescritas)
        return parametros

    def _snapshot(self, **sobrescritas):
        return self.interface.previsualizar_publicacao(
            **self._parametros(**sobrescritas)
        )["snapshot_fingerprint"]

    def _emitir(self, validade_segundos=60, **sobrescritas):
        parametros = self._parametros(**sobrescritas)
        return self.emissor.emitir(
            contexto_operador=self.contexto_operador,
            snapshot_fingerprint=self._snapshot(**sobrescritas),
            validade_segundos=validade_segundos,
            **parametros,
        )

    def _solicitar(
        self,
        autorizacao,
        chave_idempotencia="request-supervised",
        snapshot_esperado=None,
        **sobrescritas,
    ):
        parametros = self._parametros(**sobrescritas)
        return self.interface.solicitar_publicacao_supervisionada(
            autorizacao=autorizacao,
            chave_idempotencia=chave_idempotencia,
            snapshot_esperado=(
                snapshot_esperado
                if snapshot_esperado is not None
                else (
                    autorizacao.snapshot_fingerprint
                    if autorizacao is not None else None
                )
            ),
            **parametros,
        )

    def _contagens(self):
        conexao = database.conectar_banco()
        try:
            return {
                tabela: conexao.execute(
                    f"SELECT COUNT(*) AS quantidade FROM {tabela};"
                ).fetchone()["quantidade"]
                for tabela in (
                    "publicacoes",
                    "fila_publicacao",
                    "etapas_publicacao",
                    "historico_publicacao",
                    "idempotencia_solicitacao_publicacao",
                    "autorizacoes_publicacao_consumidas",
                )
            }
        finally:
            conexao.close()

    def test_autorizacao_valida_cria_solicitacao_e_auditoria_atomica(self):
        autorizacao = self._emitir()

        resultado = self._solicitar(autorizacao)

        self.assertEqual("AGUARDANDO", resultado["status"])
        self.assertFalse(resultado["execucao_autorizada"])
        self.assertEqual(
            {
                "publicacoes": 1,
                "fila_publicacao": 1,
                "etapas_publicacao": 6,
                "historico_publicacao": 1,
                "idempotencia_solicitacao_publicacao": 1,
                "autorizacoes_publicacao_consumidas": 1,
            },
            self._contagens(),
        )
        conexao = database.conectar_banco()
        try:
            auditoria = conexao.execute(
                """
                SELECT *
                FROM autorizacoes_publicacao_consumidas
                WHERE autorizacao_id = ?;
                """,
                (autorizacao.autorizacao_id,),
            ).fetchone()
        finally:
            conexao.close()
        self.assertIsNotNone(auditoria)
        self.assertEqual("operador-confiavel", auditoria["autorizador_id"])
        self.assertEqual(resultado["publicacao_id"], auditoria["publicacao_id"])
        self.assertNotIn("assinatura", auditoria.keys())

    def test_caminho_supervisionado_bloqueia_sem_emissor_ou_autorizacao(self):
        autorizacao = self._emitir()
        interface_bloqueada = InterfaceAutoTube(ServicoPublicacaoDB())

        with self.assertRaisesRegex(
            RuntimeError,
            "authorization_issuer_unavailable",
        ):
            interface_bloqueada.solicitar_publicacao_supervisionada(
                autorizacao=autorizacao,
                chave_idempotencia="request-disabled",
                snapshot_esperado=autorizacao.snapshot_fingerprint,
                **self._parametros(),
            )
        with self.assertRaisesRegex(RuntimeError, "authorization_required"):
            self._solicitar(None)
        self.assertEqual(0, self._contagens()["publicacoes"])

    def test_autorizacao_expirada_e_rejeitada(self):
        autorizacao = self._emitir(validade_segundos=30)
        self.relogio.avancar(31)

        with self.assertRaisesRegex(RuntimeError, "authorization_expired"):
            self._solicitar(autorizacao)

        self.assertEqual(0, self._contagens()["publicacoes"])

    def test_expiracao_e_revalidada_dentro_da_transacao(self):
        autorizacao = self._emitir(validade_segundos=30)
        criar_original = repositorio_publicacao.criar_solicitacao_atomica

        def criar_apos_expiracao(**parametros):
            self.relogio.avancar(31)
            return criar_original(**parametros)

        with patch(
            "core.servico_publicacao_db.criar_solicitacao_atomica",
            side_effect=criar_apos_expiracao,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "authorization_expired",
            ):
                self._solicitar(autorizacao)

        self.assertEqual(0, self._contagens()["publicacoes"])

    def test_assinatura_parametros_e_snapshot_divergentes_sao_rejeitados(self):
        autorizacao = self._emitir()
        adulterada = replace(
            autorizacao,
            autorizador_id="operador-forjado",
        )

        with self.assertRaisesRegex(RuntimeError, "authorization_invalid"):
            self._solicitar(
                {"autorizador_id": "operador-arbitrario"},
                snapshot_esperado=autorizacao.snapshot_fingerprint,
            )
        with self.assertRaisesRegex(RuntimeError, "authorization_invalid"):
            self._solicitar(adulterada)
        with self.assertRaisesRegex(RuntimeError, "authorization_mismatch"):
            self._solicitar(autorizacao, privacidade="unlisted")
        with self.assertRaisesRegex(RuntimeError, "authorization_mismatch"):
            self._solicitar(
                autorizacao,
                snapshot_esperado="sha256:" + "0" * 64,
            )
        self.assertEqual(0, self._contagens()["publicacoes"])

    def test_caminho_supervisionado_exige_chave_e_snapshot(self):
        autorizacao = self._emitir()

        with self.assertRaisesRegex(RuntimeError, "idempotency_key_required"):
            self.interface.solicitar_publicacao_supervisionada(
                autorizacao=autorizacao,
                chave_idempotencia=None,
                snapshot_esperado=autorizacao.snapshot_fingerprint,
                **self._parametros(),
            )
        with self.assertRaisesRegex(RuntimeError, "snapshot_required"):
            self.interface.solicitar_publicacao_supervisionada(
                autorizacao=autorizacao,
                chave_idempotencia="request-without-snapshot",
                snapshot_esperado=None,
                **self._parametros(),
            )
        self.assertEqual(0, self._contagens()["publicacoes"])

    def test_migracao_de_autorizacao_e_idempotente_e_preserva_dados(self):
        conexao = database.conectar_banco()
        try:
            dados_antes = tuple(conexao.execute(
                "SELECT id, status FROM conteudos ORDER BY id;"
            ).fetchone())
            conexao.execute(
                "DROP TABLE autorizacoes_publicacao_consumidas;"
            )
            conexao.commit()

            database.migrar_autorizacao_supervisionada_publicacao(conexao)
            conexao.commit()
            database.migrar_autorizacao_supervisionada_publicacao(conexao)
            conexao.commit()
            dados_depois = tuple(conexao.execute(
                "SELECT id, status FROM conteudos ORDER BY id;"
            ).fetchone())
        finally:
            conexao.close()

        self.assertEqual(dados_antes, dados_depois)
        resultado = self._solicitar(self._emitir())
        self.assertEqual("AGUARDANDO", resultado["status"])
        self.assertEqual(
            1,
            self._contagens()["autorizacoes_publicacao_consumidas"],
        )

    def test_autorizacao_nao_pode_ser_reutilizada_com_outra_chave(self):
        autorizacao = self._emitir()
        primeiro = self._solicitar(
            autorizacao,
            chave_idempotencia="request-first",
        )
        contagens_antes = self._contagens()

        with self.assertRaisesRegex(
            RuntimeError,
            "authorization_already_used",
        ):
            self._solicitar(
                autorizacao,
                chave_idempotencia="request-second",
            )

        self.assertEqual(1, self._contagens()["publicacoes"])
        self.assertEqual(contagens_antes, self._contagens())
        self.assertTrue(primeiro["publicacao_id"])

    def test_recuperacao_idempotente_nao_reconsome_autorizacao_expirada(self):
        autorizacao = self._emitir(validade_segundos=30)
        primeiro = self._solicitar(autorizacao)
        self.relogio.avancar(31)

        segundo = self._solicitar(autorizacao)

        self.assertEqual(primeiro, segundo)
        self.assertEqual(1, self._contagens()["publicacoes"])
        self.assertEqual(
            1,
            self._contagens()["autorizacoes_publicacao_consumidas"],
        )

    def test_concorrencia_consume_autorizacao_uma_unica_vez(self):
        autorizacao = self._emitir()
        barreira = threading.Barrier(2)
        resultados = []
        erros = []

        def solicitar(chave):
            try:
                barreira.wait(timeout=2)
                resultados.append(self._solicitar(
                    autorizacao,
                    chave_idempotencia=chave,
                ))
            except Exception as erro:
                erros.append(erro)

        threads = [
            threading.Thread(target=solicitar, args=("request-race-1",)),
            threading.Thread(target=solicitar, args=("request-race-2",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        self.assertEqual(1, len(resultados))
        self.assertEqual(1, len(erros))
        self.assertEqual(
            "authorization_already_used",
            getattr(erros[0], "codigo", None),
        )
        self.assertEqual(1, self._contagens()["publicacoes"])
        self.assertEqual(
            1,
            self._contagens()["autorizacoes_publicacao_consumidas"],
        )

    def test_falha_na_auditoria_reverte_toda_a_criacao(self):
        autorizacao = self._emitir()
        conexao = database.conectar_banco()
        try:
            conexao.execute(
                """
                CREATE TRIGGER falhar_auditoria_autorizacao
                BEFORE INSERT ON autorizacoes_publicacao_consumidas
                BEGIN
                    SELECT RAISE(ABORT, 'falha simulada');
                END;
                """
            )
            conexao.commit()
        finally:
            conexao.close()

        with self.assertRaises(sqlite3.IntegrityError):
            self._solicitar(autorizacao)

        self.assertEqual(
            {
                "publicacoes": 0,
                "fila_publicacao": 0,
                "etapas_publicacao": 0,
                "historico_publicacao": 0,
                "idempotencia_solicitacao_publicacao": 0,
                "autorizacoes_publicacao_consumidas": 0,
            },
            self._contagens(),
        )

    def test_caminho_legado_permanece_compativel(self):
        resultado = InterfaceAutoTube(
            ServicoPublicacaoDB()
        ).solicitar_publicacao(
            conteudo_id="conteudo-1",
            canal_id="UC1234567890",
        )

        self.assertEqual("AGUARDANDO", resultado["status"])
        self.assertEqual(1, self._contagens()["publicacoes"])
        self.assertEqual(
            0,
            self._contagens()["autorizacoes_publicacao_consumidas"],
        )

    def test_consulta_idempotente_recupera_apos_reinicio_sem_efeitos(self):
        resultado = self._solicitar(self._emitir())
        contagens_antes = self._contagens()
        bytes_antes = self.db_path.read_bytes()

        interface_reiniciada = InterfaceAutoTube(
            ServicoPublicacaoDB(emissor_autorizacao=self.emissor)
        )
        consulta = interface_reiniciada.consultar_solicitacao_supervisionada(
            "request-supervised"
        )

        self.assertEqual(resultado["publicacao_id"], consulta["publicacao_id"])
        self.assertEqual("BLOQUEADA", consulta["estado_supervisao"])
        self.assertEqual("AGUARDANDO", consulta["status_publicacao"])
        self.assertEqual("AGUARDANDO", consulta["status_fila"])
        self.assertTrue(consulta["execucao_bloqueada"])
        self.assertFalse(consulta["execucao_autorizada"])
        self.assertNotIn("conteudo", consulta)
        self.assertNotIn("metadados", consulta)
        self.assertNotIn("video_pipeline", consulta)
        self.assertEqual(contagens_antes, self._contagens())
        self.assertEqual(bytes_antes, self.db_path.read_bytes())

    def test_consulta_inexistente_e_somente_leitura(self):
        bytes_antes = self.db_path.read_bytes()

        consulta = self.interface.consultar_solicitacao_supervisionada(
            "request-inexistente"
        )

        self.assertEqual(
            {
                "encontrada": False,
                "estado_supervisao": "NAO_ENCONTRADA",
                "execucao_autorizada": False,
            },
            consulta,
        )
        self.assertEqual(bytes_antes, self.db_path.read_bytes())

    def test_solicitacao_supervisionada_fica_fora_dos_workers(self):
        resultado = self._solicitar(self._emitir())
        servico_reiniciado = ServicoPublicacaoDB(
            emissor_autorizacao=self.emissor
        )

        self.assertIsNone(servico_reiniciado.consultar_proximo_job())
        with patch(
            "core.servico_publicacao_db.processar_publicacao"
        ) as processar:
            self.assertIsNone(
                servico_reiniciado.executar_proxima_publicacao()
            )
            with self.assertRaisesRegex(
                RuntimeError,
                "supervision_execution_blocked",
            ):
                servico_reiniciado.executar_job(resultado["publicacao_id"])
        processar.assert_not_called()

        conexao = database.conectar_banco()
        try:
            bloqueio = conexao.execute(
                """
                SELECT execucao_bloqueada
                FROM solicitacoes_publicacao_supervisionadas
                WHERE publicacao_id = ?;
                """,
                (resultado["publicacao_id"],),
            ).fetchone()
            with self.assertRaises(sqlite3.IntegrityError):
                conexao.execute(
                    """
                    UPDATE solicitacoes_publicacao_supervisionadas
                    SET execucao_bloqueada = 0
                    WHERE publicacao_id = ?;
                    """,
                    (resultado["publicacao_id"],),
                )
        finally:
            conexao.close()
        self.assertEqual(1, bloqueio["execucao_bloqueada"])

    def test_worker_legado_permanece_compativel(self):
        resultado = InterfaceAutoTube(
            ServicoPublicacaoDB()
        ).solicitar_publicacao(
            conteudo_id="conteudo-1",
            canal_id="UC1234567890",
        )

        job = ServicoPublicacaoDB().consultar_proximo_job()

        self.assertEqual(resultado["publicacao_id"], job["publicacao_id"])


if __name__ == "__main__":
    unittest.main()
