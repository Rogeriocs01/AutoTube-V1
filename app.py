from menu import iniciar
from core.logger import obter_logger
from version import obter_identificacao


logger = obter_logger()


if __name__ == "__main__":
    logger.info(
        "AutoTube iniciado | %s",
        obter_identificacao(),
    )

    try:
        iniciar()
    finally:
        logger.info(
            "AutoTube encerrado"
        )