import json

from config import BASE_DIR


APP_NAME = "AutoTube"
APP_VERSION = "1.1.1"

ARQUIVO_AMBIENTE = (
    BASE_DIR
    / "ambiente.json"
)


def obter_ambiente():
    """
    Obtém o ambiente local da instalação.

    O arquivo ambiente.json não é versionado.

    Exemplos:

    Development:
    {
        "ambiente": "DEVELOPMENT"
    }

    Stable:
    {
        "ambiente": "STABLE"
    }
    """

    if not ARQUIVO_AMBIENTE.exists():
        return "DEVELOPMENT"

    try:
        dados = json.loads(
            ARQUIVO_AMBIENTE.read_text(
                encoding="utf-8"
            )
        )

        ambiente = str(
            dados.get(
                "ambiente",
                "DEVELOPMENT",
            )
        ).upper()

        if ambiente in {
            "DEVELOPMENT",
            "STABLE",
        }:
            return ambiente

    except (
        json.JSONDecodeError,
        OSError,
    ):
        pass

    return "DEVELOPMENT"


def obter_identificacao():
    ambiente = obter_ambiente()

    if ambiente == "DEVELOPMENT":
        versao = (
            f"{APP_VERSION}-dev"
        )
    else:
        versao = APP_VERSION

    return (
        f"{APP_NAME} V{versao} "
        f"— {ambiente}"
    )