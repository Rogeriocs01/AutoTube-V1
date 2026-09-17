from core.logger import obter_logger

from core.pipeline import processar_publicacao

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