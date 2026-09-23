from core.logger import obter_logger

from core.pipeline import (
    excluir_arquivo_temporario,
    processar_publicacao,
)

from core.drive import (
    baixar_thumbnail,
    mover_video_para_publicados,
)

from core.youtube import (
    adicionar_video_playlist,
    definir_thumbnail_youtube,
)

from core.repositorio import (
    obter_conteudo,
    obter_metadados,
)

from core.repositorio_publicacao import (
    adicionar_na_fila,
    atualizar_item_fila,
    atualizar_publicacao,
    criar_publicacao,
    incrementar_tentativa_fila,
    incrementar_tentativa_etapa,
    listar_etapas,
    listar_fila,
    obter_item_fila,
    obter_publicacao,
    registrar_historico,
    salvar_etapa,
    atualizar_etapa,
)


logger = obter_logger()


PLATAFORMA_YOUTUBE = "YOUTUBE"


class ServicoPublicacaoDB:
    """
    Serviço de publicação baseado no SQLite.

    Responsabilidades:

    - localizar conteúdo
    - localizar metadados
    - validar dados mínimos
    - adaptar conteúdo para o pipeline atual
    - criar publicação
    - adicionar publicação à fila
    - preparar execução
    - executar publicação
    - registrar estados no SQLite

    O pipeline atual continua responsável
    pela execução técnica da publicação.
    """

    def obter_dados_conteudo(
        self,
        conteudo_id,
    ):
        conteudo = obter_conteudo(
            conteudo_id
        )

        if conteudo is None:
            raise ValueError(
                f"Conteúdo não encontrado: "
                f"{conteudo_id}"
            )

        metadados = obter_metadados(
            conteudo_id
        )

        if metadados is None:
            raise ValueError(
                f"Metadados não encontrados: "
                f"{conteudo_id}"
            )

        return conteudo, metadados

    def validar_conteudo(
        self,
        conteudo,
        metadados,
    ):
        erros = []

        if not conteudo.get(
            "id_legado"
        ):
            erros.append(
                "ID legado não informado"
            )

        if not conteudo.get(
            "nome_arquivo"
        ):
            erros.append(
                "Nome do arquivo não informado"
            )

        if not conteudo.get(
            "drive_file_id"
        ):
            erros.append(
                "Drive File ID não informado"
            )

        if not metadados.get(
            "titulo"
        ):
            erros.append(
                "Título não informado"
            )

        if erros:
            raise ValueError(
                "; ".join(erros)
            )

        return True

    def adaptar_video_pipeline(
        self,
        conteudo,
    ):
        """
        Converte o formato SQLite para
        o formato esperado atualmente
        pelo pipeline legado.
        """

        return {
            "arquivo": conteudo[
                "nome_arquivo"
            ],
            "drive_id": conteudo[
                "drive_file_id"
            ],
            "tipo_conteudo": conteudo.get(
                "tipo"
            ),
            "status": conteudo.get(
                "status"
            ),
        }

    def criar_solicitacao(
        self,
        conteudo_id,
        privacidade="private",
        canal_id=None,
        prioridade=100,
    ):
        """
        Cria uma solicitação de publicação
        e adiciona à fila.

        Não executa upload.
        """

        conteudo, metadados = (
            self.obter_dados_conteudo(
                conteudo_id
            )
        )

        self.validar_conteudo(
            conteudo,
            metadados,
        )

        publicacao_id = criar_publicacao(
            conteudo_id=conteudo_id,
            plataforma=PLATAFORMA_YOUTUBE,
            canal_id=canal_id,
            privacidade=privacidade,
            status="AGUARDANDO",
        )

        adicionar_na_fila(
            publicacao_id=publicacao_id,
            prioridade=prioridade,
            status="AGUARDANDO",
        )

        self.criar_etapas_youtube(
            publicacao_id
        )

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa="CRIACAO",
            status="AGUARDANDO",
            mensagem=(
                "Solicitação de publicação criada"
            ),
        )

        logger.info(
            "Solicitação de publicação criada | "
            "publicacao_id=%s | "
            "conteudo_id=%s | "
            "plataforma=%s",
            publicacao_id,
            conteudo_id,
            PLATAFORMA_YOUTUBE,
        )

        return {
            "publicacao_id": publicacao_id,
            "conteudo": conteudo,
            "metadados": metadados,
            "video_pipeline": (
                self.adaptar_video_pipeline(
                    conteudo
                )
            ),
        }

    def criar_etapas_youtube(
        self,
        publicacao_id,
    ):
        """
        Define as etapas previstas
        para publicação no YouTube.

        O controle detalhado dessas etapas
        será aprofundado na V1.2.6.
        """

        salvar_etapa(
            publicacao_id=publicacao_id,
            etapa="PREPARACAO",
            status="AGUARDANDO",
            obrigatoria=True,
        )

        salvar_etapa(
            publicacao_id=publicacao_id,
            etapa="UPLOAD",
            status="AGUARDANDO",
            obrigatoria=True,
        )

        salvar_etapa(
            publicacao_id=publicacao_id,
            etapa="PLAYLIST",
            status="AGUARDANDO",
            obrigatoria=False,
        )

        salvar_etapa(
            publicacao_id=publicacao_id,
            etapa="THUMBNAIL",
            status="AGUARDANDO",
            obrigatoria=False,
        )

        salvar_etapa(
            publicacao_id=publicacao_id,
            etapa="DRIVE",
            status="AGUARDANDO",
            obrigatoria=False,
        )

        salvar_etapa(
            publicacao_id=publicacao_id,
            etapa="FINALIZACAO",
            status="AGUARDANDO",
            obrigatoria=True,
        )

    def registrar_evento_etapa(
        self,
        publicacao_id,
        etapa,
        status,
        mensagem=None,
        dados=None,
    ):
        """Persiste no SQLite um evento técnico do pipeline."""
        from core.repositorio_publicacao import agora_iso

        dados = dados or {}
        agora = agora_iso()

        if status == "PROCESSANDO":
            incrementar_tentativa_etapa(publicacao_id, etapa)
            atualizar_etapa(
                publicacao_id=publicacao_id,
                etapa=etapa,
                status="PROCESSANDO",
                data_inicio=agora,
                ultimo_erro="",
            )
        elif status in ("CONCLUIDO", "IGNORADO"):
            atualizar_etapa(
                publicacao_id=publicacao_id,
                etapa=etapa,
                status=status,
                data_conclusao=agora,
                ultimo_erro="",
            )
        elif status == "ERRO":
            atualizar_etapa(
                publicacao_id=publicacao_id,
                etapa=etapa,
                status="ERRO",
                data_conclusao=agora,
                ultimo_erro=mensagem or "Falha na etapa",
            )
        else:
            atualizar_etapa(
                publicacao_id=publicacao_id,
                etapa=etapa,
                status=status,
            )

        youtube_id = dados.get("youtube_id")
        if etapa == "UPLOAD" and status == "CONCLUIDO" and youtube_id:
            atualizar_publicacao(
                publicacao_id=publicacao_id,
                external_id=youtube_id,
            )

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa=etapa,
            status=status,
            mensagem=mensagem,
            detalhes=(
                f"youtube_id={youtube_id}"
                if youtube_id else None
            ),
        )

    def criar_callback_etapas(self, publicacao_id):
        """Cria callback de etapas sem acoplar o pipeline ao SQLite."""
        def callback(etapa, status, mensagem=None, dados=None):
            self.registrar_evento_etapa(
                publicacao_id=publicacao_id,
                etapa=etapa,
                status=status,
                mensagem=mensagem,
                dados=dados,
            )

        return callback

    def obter_solicitacao(
        self,
        publicacao_id,
    ):
        return obter_publicacao(
            publicacao_id
        )

    def preparar_execucao(
        self,
        publicacao_id,
    ):
        """
        Monta todos os dados necessários
        para executar uma publicação.
        """

        publicacao = obter_publicacao(
            publicacao_id
        )

        if publicacao is None:
            raise ValueError(
                f"Publicação não encontrada: "
                f"{publicacao_id}"
            )

        item_fila = obter_item_fila(
            publicacao_id
        )

        if item_fila is None:
            raise ValueError(
                f"Publicação não está na fila: "
                f"{publicacao_id}"
            )

        plataforma = publicacao.get(
            "plataforma"
        )

        if plataforma != PLATAFORMA_YOUTUBE:
            raise ValueError(
                "Plataforma ainda não suportada: "
                f"{plataforma}"
            )

        conteudo_id = publicacao[
            "conteudo_id"
        ]

        conteudo, metadados = (
            self.obter_dados_conteudo(
                conteudo_id
            )
        )

        self.validar_conteudo(
            conteudo,
            metadados,
        )

        pacote = {
            "publicacao_id": (
                publicacao_id
            ),
            "conteudo_id": (
                conteudo_id
            ),
            "video_id": conteudo[
                "id_legado"
            ],
            "video": (
                self.adaptar_video_pipeline(
                    conteudo
                )
            ),
            "metadados": metadados,
            "privacidade": (
                publicacao.get(
                    "privacidade"
                )
                or "private"
            ),
            "plataforma": plataforma,
            "canal_id": publicacao.get(
                "canal_id"
            ),
            "publicacao": publicacao,
            "fila": item_fila,
        }

        logger.info(
            "Execução preparada | "
            "publicacao_id=%s | "
            "conteudo_id=%s | "
            "video_id=%s | "
            "plataforma=%s",
            publicacao_id,
            conteudo_id,
            conteudo["id_legado"],
            plataforma,
        )

        return pacote

    def obter_proxima_execucao(
        self,
    ):
        """
        Retorna a próxima publicação
        aguardando na fila.
        """

        fila = listar_fila(
            status="AGUARDANDO"
        )

        if not fila:
            return None

        proximo = fila[0]

        return self.preparar_execucao(
            proximo["publicacao_id"]
        )

    def iniciar_processamento(
        self,
        publicacao_id,
    ):
        """
        Marca publicação e fila
        como PROCESSANDO.
        """

        from core.repositorio_publicacao import (
            agora_iso,
        )

        agora = agora_iso()

        atualizar_publicacao(
            publicacao_id=publicacao_id,
            status="PROCESSANDO",
            data_inicio=agora,
        )

        incrementar_tentativa_fila(
            publicacao_id
        )

        atualizar_item_fila(
            publicacao_id=publicacao_id,
            status="PROCESSANDO",
            iniciado_em=agora,
            ultimo_erro="",
        )

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa="EXECUCAO",
            status="PROCESSANDO",
            mensagem=(
                "Processamento da publicação iniciado"
            ),
        )

        logger.info(
            "Processamento iniciado | "
            "publicacao_id=%s",
            publicacao_id,
        )

    def finalizar_sucesso(
        self,
        publicacao_id,
        resultado,
    ):
        """
        Finaliza uma publicação considerada
        completamente concluída.
        """

        from core.repositorio_publicacao import (
            agora_iso,
        )

        agora = agora_iso()

        atualizar_publicacao(
            publicacao_id=publicacao_id,
            status="CONCLUIDO",
            external_id=resultado.youtube_id,
            data_conclusao=agora,
        )

        atualizar_item_fila(
            publicacao_id=publicacao_id,
            status="CONCLUIDO",
            finalizado_em=agora,
            ultimo_erro="",
        )

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa="FINALIZACAO",
            status="CONCLUIDO",
            mensagem=(
                "Publicação concluída com sucesso"
            ),
            detalhes=(
                f"youtube_id="
                f"{resultado.youtube_id}"
            ),
        )

        logger.info(
            "Publicação concluída | "
            "publicacao_id=%s | "
            "youtube_id=%s",
            publicacao_id,
            resultado.youtube_id,
        )

    def finalizar_parcial(
        self,
        publicacao_id,
        resultado,
        mensagem,
    ):
        """
        Marca a publicação como PARCIAL.

        Isso ocorre quando o upload principal
        foi realizado, mas alguma operação
        complementar falhou.
        """

        atualizar_publicacao(
            publicacao_id=publicacao_id,
            status="PARCIAL",
            external_id=resultado.youtube_id,
        )

        atualizar_item_fila(
            publicacao_id=publicacao_id,
            status="PARCIAL",
            ultimo_erro=mensagem,
        )

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa=(
                resultado.etapa
                or "POS_UPLOAD"
            ),
            status="PARCIAL",
            mensagem=mensagem,
            detalhes=(
                f"youtube_id="
                f"{resultado.youtube_id}"
            ),
        )

        logger.warning(
            "Publicação parcial | "
            "publicacao_id=%s | "
            "youtube_id=%s | "
            "motivo=%s",
            publicacao_id,
            resultado.youtube_id,
            mensagem,
        )

    def finalizar_erro(
        self,
        publicacao_id,
        resultado,
    ):
        """
        Marca uma publicação como ERRO
        quando o upload principal
        não foi concluído.
        """

        mensagem = (
            resultado.mensagem
            or "Falha na publicação"
        )

        atualizar_publicacao(
            publicacao_id=publicacao_id,
            status="ERRO",
        )

        atualizar_item_fila(
            publicacao_id=publicacao_id,
            status="ERRO",
            ultimo_erro=mensagem,
        )

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa=(
                resultado.etapa
                or "EXECUCAO"
            ),
            status="ERRO",
            mensagem=mensagem,
        )

        logger.error(
            "Publicação com erro | "
            "publicacao_id=%s | "
            "etapa=%s | "
            "motivo=%s",
            publicacao_id,
            resultado.etapa,
            mensagem,
        )

    def classificar_resultado(
        self,
        resultado,
    ):
        """
        Classifica o resultado do pipeline.

        CONCLUIDO:
            upload e operações complementares OK.

        PARCIAL:
            upload realizado, mas playlist,
            thumbnail, Drive ou etapa posterior
            apresentou problema.

        ERRO:
            publicação principal não concluída.
        """

        if not resultado.sucesso:
            if resultado.youtube_id:
                return "PARCIAL"

            return "ERRO"

        if resultado.playlist_ok is False:
            return "PARCIAL"

        if resultado.thumbnail_ok is False:
            return "PARCIAL"

        if resultado.drive_ok is False:
            return "PARCIAL"

        return "CONCLUIDO"

    def obter_plano_reparo(
        self,
        publicacao_id,
    ):
        """
        Monta o plano de reparo de uma publicação PARCIAL.

        Somente leitura: não chama YouTube, não chama Drive,
        não altera o SQLite e nunca agenda novo UPLOAD.
        """

        publicacao = obter_publicacao(publicacao_id)

        if publicacao is None:
            raise ValueError(
                f"Publicação não encontrada: {publicacao_id}"
            )

        if publicacao.get("plataforma") != PLATAFORMA_YOUTUBE:
            raise ValueError(
                "Reparo disponível somente para publicações do YouTube."
            )

        status_publicacao = publicacao.get("status")

        if status_publicacao != "PARCIAL":
            raise RuntimeError(
                "Reparo permitido somente para publicação "
                f"com status PARCIAL. Status atual: {status_publicacao}"
            )

        external_id = str(
            publicacao.get("external_id") or ""
        ).strip()

        if not external_id:
            mensagem = (
                "Publicação PARCIAL sem external_id. "
                "Reparo bloqueado por segurança para evitar upload duplicado."
            )
            registrar_historico(
                publicacao_id=publicacao_id,
                etapa="SEGURANCA",
                status="BLOQUEADO",
                mensagem=mensagem,
            )
            logger.warning(
                "Reparo bloqueado | publicacao_id=%s | "
                "motivo=external_id ausente",
                publicacao_id,
            )
            raise RuntimeError(mensagem)

        etapas = listar_etapas(publicacao_id)
        etapas_por_nome = {
            etapa["etapa"]: etapa
            for etapa in etapas
        }

        upload = etapas_por_nome.get("UPLOAD")
        if upload is None:
            raise RuntimeError(
                "Etapa UPLOAD não encontrada. "
                "Reparo bloqueado por segurança."
            )

        reparar = []
        resolvidas = []
        revisar = []

        for nome_etapa in ("PLAYLIST", "THUMBNAIL", "DRIVE"):
            etapa = etapas_por_nome.get(nome_etapa)

            if etapa is None:
                revisar.append(nome_etapa)
                continue

            status = etapa.get("status")

            if status == "ERRO":
                reparar.append(nome_etapa)
            elif status in ("CONCLUIDO", "IGNORADO"):
                resolvidas.append(nome_etapa)
            else:
                revisar.append(nome_etapa)

        plano = {
            "publicacao_id": publicacao_id,
            "youtube_id": external_id,
            "status_publicacao": status_publicacao,
            "upload_bloqueado": True,
            "upload_status": upload.get("status"),
            "reparar": reparar,
            "resolvidas": resolvidas,
            "revisar": revisar,
        }

        logger.info(
            "Plano de reparo criado | publicacao_id=%s | "
            "youtube_id=%s | reparar=%s | revisar=%s",
            publicacao_id,
            external_id,
            reparar,
            revisar,
        )

        return plano

    def validar_plano_reparo(
        self,
        publicacao_id,
    ):
        """
        Valida o plano sem executar nenhuma operação externa.
        """

        plano = self.obter_plano_reparo(publicacao_id)

        if "UPLOAD" in plano["reparar"]:
            raise RuntimeError(
                "Falha crítica de segurança: "
                "UPLOAD apareceu no plano de reparo."
            )

        if not plano["upload_bloqueado"]:
            raise RuntimeError(
                "Falha crítica de segurança: "
                "UPLOAD não está bloqueado."
            )

        return plano

    def executar_reparo_playlist(
        self,
        publicacao_id,
        youtube_id,
        metadados,
    ):
        """Reexecuta somente a etapa PLAYLIST."""

        playlist_id = metadados.get(
            "playlist_id"
        )

        if not playlist_id:
            self.registrar_evento_etapa(
                publicacao_id,
                "PLAYLIST",
                "IGNORADO",
                "Nenhuma playlist definida",
            )
            return True

        self.registrar_evento_etapa(
            publicacao_id,
            "PLAYLIST",
            "PROCESSANDO",
            "Reparo da playlist iniciado",
        )

        ok = adicionar_video_playlist(
            youtube_id=youtube_id,
            playlist_id=playlist_id,
        )

        self.registrar_evento_etapa(
            publicacao_id,
            "PLAYLIST",
            "CONCLUIDO" if ok else "ERRO",
            (
                "Playlist reparada com sucesso"
                if ok
                else "Falha ao reparar playlist"
            ),
        )

        return bool(ok)

    def executar_reparo_thumbnail(
        self,
        publicacao_id,
        youtube_id,
        conteudo,
    ):
        """Reexecuta somente a etapa THUMBNAIL."""

        caminho_thumbnail = None

        self.registrar_evento_etapa(
            publicacao_id,
            "THUMBNAIL",
            "PROCESSANDO",
            "Reparo da thumbnail iniciado",
        )

        try:
            caminho_thumbnail = baixar_thumbnail(
                nome_video=conteudo[
                    "nome_arquivo"
                ]
            )

            if caminho_thumbnail is None:
                self.registrar_evento_etapa(
                    publicacao_id,
                    "THUMBNAIL",
                    "ERRO",
                    "Thumbnail não encontrada ou não pôde ser baixada",
                )
                return False

            ok = definir_thumbnail_youtube(
                youtube_id=youtube_id,
                caminho_thumbnail=caminho_thumbnail,
            )

            self.registrar_evento_etapa(
                publicacao_id,
                "THUMBNAIL",
                "CONCLUIDO" if ok else "ERRO",
                (
                    "Thumbnail reparada com sucesso"
                    if ok
                    else "Falha ao reparar thumbnail"
                ),
            )

            return bool(ok)

        finally:
            excluir_arquivo_temporario(
                caminho_thumbnail
            )

    def executar_reparo_drive(
        self,
        publicacao_id,
        conteudo,
    ):
        """Reexecuta somente a etapa DRIVE."""

        self.registrar_evento_etapa(
            publicacao_id,
            "DRIVE",
            "PROCESSANDO",
            "Reparo da movimentação no Drive iniciado",
        )

        ok = mover_video_para_publicados(
            drive_id=conteudo[
                "drive_file_id"
            ]
        )

        self.registrar_evento_etapa(
            publicacao_id,
            "DRIVE",
            "CONCLUIDO" if ok else "ERRO",
            (
                "Movimentação no Drive reparada com sucesso"
                if ok
                else "Falha ao reparar movimentação no Drive"
            ),
        )

        return bool(ok)

    def avaliar_reparo(
        self,
        publicacao_id,
    ):
        """
        Reavalia as etapas pós-upload após uma tentativa de reparo.
        """

        etapas = listar_etapas(
            publicacao_id
        )

        etapas_por_nome = {
            etapa["etapa"]: etapa
            for etapa in etapas
        }

        pendentes = []

        for nome_etapa in (
            "PLAYLIST",
            "THUMBNAIL",
            "DRIVE",
        ):
            etapa = etapas_por_nome.get(
                nome_etapa
            )

            if etapa is None:
                pendentes.append(
                    nome_etapa
                )
                continue

            if etapa.get("status") not in (
                "CONCLUIDO",
                "IGNORADO",
            ):
                pendentes.append(
                    nome_etapa
                )

        return {
            "concluido": not pendentes,
            "pendentes": pendentes,
        }

    def reparar_publicacao(
        self,
        publicacao_id,
    ):
        """
        Repara somente etapas pós-upload de uma publicação PARCIAL.

        REGRA CRÍTICA:
        este método nunca chama processar_publicacao()
        e nunca executa UPLOAD.
        """

        plano = self.validar_plano_reparo(
            publicacao_id
        )

        if plano["revisar"]:
            raise RuntimeError(
                "Reparo automático bloqueado. "
                "Há etapas que exigem revisão: "
                + ", ".join(plano["revisar"])
            )

        publicacao = obter_publicacao(
            publicacao_id
        )

        conteudo, metadados = (
            self.obter_dados_conteudo(
                publicacao["conteudo_id"]
            )
        )

        youtube_id = plano[
            "youtube_id"
        ]

        registrar_historico(
            publicacao_id=publicacao_id,
            etapa="REPARO",
            status="PROCESSANDO",
            mensagem=(
                "Reparo seletivo iniciado. "
                "Etapas: "
                + (
                    ", ".join(plano["reparar"])
                    if plano["reparar"]
                    else "nenhuma"
                )
            ),
        )

        resultados = {}

        for etapa in plano["reparar"]:
            try:
                if etapa == "PLAYLIST":
                    resultados[etapa] = (
                        self.executar_reparo_playlist(
                            publicacao_id,
                            youtube_id,
                            metadados,
                        )
                    )

                elif etapa == "THUMBNAIL":
                    resultados[etapa] = (
                        self.executar_reparo_thumbnail(
                            publicacao_id,
                            youtube_id,
                            conteudo,
                        )
                    )

                elif etapa == "DRIVE":
                    resultados[etapa] = (
                        self.executar_reparo_drive(
                            publicacao_id,
                            conteudo,
                        )
                    )

                else:
                    raise RuntimeError(
                        "Etapa de reparo não suportada: "
                        f"{etapa}"
                    )

            except Exception as erro:
                logger.exception(
                    "Erro durante reparo seletivo | "
                    "publicacao_id=%s | etapa=%s",
                    publicacao_id,
                    etapa,
                )

                self.registrar_evento_etapa(
                    publicacao_id,
                    etapa,
                    "ERRO",
                    str(erro),
                )

                resultados[etapa] = False

        avaliacao = self.avaliar_reparo(
            publicacao_id
        )

        from core.repositorio_publicacao import (
            agora_iso,
        )

        agora = agora_iso()

        if avaliacao["concluido"]:
            atualizar_publicacao(
                publicacao_id=publicacao_id,
                status="CONCLUIDO",
                data_conclusao=agora,
            )

            atualizar_item_fila(
                publicacao_id=publicacao_id,
                status="CONCLUIDO",
                finalizado_em=agora,
                ultimo_erro="",
            )

            registrar_historico(
                publicacao_id=publicacao_id,
                etapa="REPARO",
                status="CONCLUIDO",
                mensagem=(
                    "Reparo seletivo concluído com sucesso"
                ),
                detalhes=(
                    f"youtube_id={youtube_id}"
                ),
            )

            status_final = "CONCLUIDO"

        else:
            mensagem = (
                "Reparo parcial. Etapas ainda pendentes: "
                + ", ".join(
                    avaliacao["pendentes"]
                )
            )

            atualizar_publicacao(
                publicacao_id=publicacao_id,
                status="PARCIAL",
            )

            atualizar_item_fila(
                publicacao_id=publicacao_id,
                status="PARCIAL",
                ultimo_erro=mensagem,
            )

            registrar_historico(
                publicacao_id=publicacao_id,
                etapa="REPARO",
                status="PARCIAL",
                mensagem=mensagem,
                detalhes=(
                    f"youtube_id={youtube_id}"
                ),
            )

            status_final = "PARCIAL"

        return {
            "publicacao_id": publicacao_id,
            "youtube_id": youtube_id,
            "upload_executado": False,
            "etapas_planejadas": (
                plano["reparar"]
            ),
            "resultados": resultados,
            "status_final": status_final,
            "pendentes": (
                avaliacao["pendentes"]
            ),
        }

    def executar_publicacao(
        self,
        publicacao_id,
    ):

        pacote = self.preparar_execucao(
            publicacao_id
        )

        publicacao = pacote[
            "publicacao"
        ]

        fila = pacote[
            "fila"
        ]

        status_publicacao = (
            publicacao.get(
                "status"
            )
        )

        status_fila = fila.get(
            "status"
        )

        tentativas = (
            fila.get(
                "tentativas"
            )
            or 0
        )

        max_tentativas = (
            fila.get(
                "max_tentativas"
            )
            or 0
        )

        # ---------------------------------
        # TRAVA 1
        # Publicação já concluída
        # ---------------------------------

        if (
            status_publicacao
            == "CONCLUIDO"
        ):
            raise RuntimeError(
                "Publicação já concluída. "
                "Nova execução bloqueada."
            )

        # ---------------------------------
        # TRAVA 2
        # Publicação parcial
        # ---------------------------------

        if (
            status_publicacao
            == "PARCIAL"
        ):
            raise RuntimeError(
                "Publicação parcial detectada. "
                "Nova execução completa bloqueada "
                "para evitar upload duplicado."
            )

        # ---------------------------------
        # TRAVA 3
        # Fila concluída ou parcial
        # ---------------------------------

        if status_fila in (
            "CONCLUIDO",
            "PARCIAL",
        ):
            raise RuntimeError(
                "Item da fila não pode ser "
                "executado novamente. "
                f"Status atual: {status_fila}"
            )

        # ---------------------------------
        # TRAVA 4
        # Limite de tentativas
        # ---------------------------------

        if (
            max_tentativas > 0
            and tentativas
            >= max_tentativas
        ):
            mensagem = (
                "Limite máximo de tentativas "
                "atingido. "
                f"Tentativas: {tentativas}/"
                f"{max_tentativas}"
            )

            registrar_historico(
                publicacao_id=publicacao_id,
                etapa="SEGURANCA",
                status="BLOQUEADO",
                mensagem=mensagem,
            )

            logger.warning(
                "Execução bloqueada | "
                "publicacao_id=%s | "
                "tentativas=%s | "
                "max_tentativas=%s",
                publicacao_id,
                tentativas,
                max_tentativas,
            )

            raise RuntimeError(
                mensagem
            )

        # ---------------------------------
        # EXECUÇÃO
        # ---------------------------------

        self.iniciar_processamento(
            publicacao_id
        )

        try:
            resultado = processar_publicacao(
                video_id=pacote[
                    "video_id"
                ],
                video=pacote[
                    "video"
                ],
                privacidade=pacote[
                    "privacidade"
                ],
                pedir_confirmacao=False,
                metadados_override=pacote[
                    "metadados"
                ],
                registrar_controle_legado=False,
                callback_etapa=self.criar_callback_etapas(
                    publicacao_id
                ),
            )

        except Exception as erro:
            logger.exception(
                "Erro inesperado durante publicação | "
                "publicacao_id=%s",
                publicacao_id,
            )

            from core.resultado_publicacao import (
                ResultadoPublicacao,
            )

            resultado = ResultadoPublicacao.falha(
                mensagem=str(erro),
                video_id=pacote[
                    "video_id"
                ],
                etapa="excecao",
            )

        classificacao = (
            self.classificar_resultado(
                resultado
            )
        )

        if classificacao == "CONCLUIDO":
            self.finalizar_sucesso(
                publicacao_id,
                resultado,
            )

        elif classificacao == "PARCIAL":
            mensagem = (
                resultado.mensagem
                or
                "Publicação concluída parcialmente"
            )

            if resultado.sucesso:
                falhas = []

                if (
                    resultado.playlist_ok
                    is False
                ):
                    falhas.append(
                        "playlist"
                    )

                if (
                    resultado.thumbnail_ok
                    is False
                ):
                    falhas.append(
                        "thumbnail"
                    )

                if (
                    resultado.drive_ok
                    is False
                ):
                    falhas.append(
                        "Drive"
                    )

                if falhas:
                    mensagem = (
                        "Falha parcial em: "
                        + ", ".join(falhas)
                    )

            self.finalizar_parcial(
                publicacao_id,
                resultado,
                mensagem,
            )

        else:
            self.finalizar_erro(
                publicacao_id,
                resultado,
            )

        return resultado

    def executar_proxima_publicacao(
        self,
    ):
        """
        Executa a próxima publicação
        aguardando na fila.

        ATENÇÃO:
        pode realizar publicação real.
        """

        pacote = (
            self.obter_proxima_execucao()
        )

        if pacote is None:
            logger.info(
                "Fila sem publicações aguardando"
            )

            return None

        return self.executar_publicacao(
            pacote["publicacao_id"]
        )


servico_publicacao_db = (
    ServicoPublicacaoDB()
)