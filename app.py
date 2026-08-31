from menu import iniciar
from core.logger import obter_logger
from version import obter_identificacao


logger = obter_logger()


def mostrar_erro_fatal():
    print(
        "\n========================================"
    )
    print(
        "          ERRO INESPERADO"
    )
    print(
        "========================================"
    )
    print()
    print(
        "O AutoTube encontrou um erro "
        "que impediu a continuação."
    )
    print()
    print(
        "Os detalhes técnicos foram "
        "registrados no arquivo de log."
    )
    print()
    print(
        "Você pode consultar a pasta:"
    )
    print(
        "logs"
    )
    print(
        "========================================"
    )

    try:
        input(
            "\nPressione ENTER para encerrar..."
        )
    except (EOFError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    logger.info(
        "AutoTube iniciado | %s",
        obter_identificacao(),
    )

    try:
        iniciar()

    except KeyboardInterrupt:
        print(
            "\n\nAutoTube interrompido pelo usuário."
        )

        logger.info(
            "AutoTube interrompido pelo usuário"
        )

    except Exception:
        logger.exception(
            "Erro fatal não tratado"
        )

        mostrar_erro_fatal()

    finally:
        logger.info(
            "AutoTube encerrado"
        )