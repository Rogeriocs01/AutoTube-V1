from core.controle import (
    obter_proximo_video_pendente,
)

from core.logger import obter_logger

from core.pipeline import (
    processar_publicacao,
)

from core.resultado_publicacao import (
    ResultadoPublicacao,
)


logger = obter_logger()


class ServicoPublicacao:
    """
    Fachada de acesso à lógica de publicação.

    Esta camada não solicita dados ao usuário
    através de input().

    Pode ser utilizada futuramente por:
    - API
    - Creator OS
    - workers
    - filas de publicação
    - outros clientes do AutoTube
    """

    def publicar(
        self,
        video_id,
        video,
        privacidade,
    ):
        logger.info(
            "Serviço de publicação acionado | "
            "video_id=%s | privacidade=%s",
            video_id,
            privacidade,
        )

        return processar_publicacao(
            video_id=video_id,
            video=video,
            privacidade=privacidade,
            pedir_confirmacao=False,
        )

    def publicar_proximo(
        self,
        privacidade,
    ):
        video_id, video = (
            obter_proximo_video_pendente()
        )

        if video is None:
            logger.info(
                "Serviço de publicação | "
                "nenhum vídeo pendente"
            )

            return ResultadoPublicacao.falha(
                mensagem=(
                    "Nenhum vídeo pendente encontrado"
                ),
                etapa="selecao_video",
            )

        return self.publicar(
            video_id=video_id,
            video=video,
            privacidade=privacidade,
        )


servico_publicacao = ServicoPublicacao()