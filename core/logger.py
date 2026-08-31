import logging
from datetime import datetime

from config import PASTA_LOGS


_logger = None


def obter_logger():
    global _logger

    if _logger is not None:
        return _logger

    PASTA_LOGS.mkdir(
        parents=True,
        exist_ok=True,
    )

    data_atual = datetime.now().strftime(
        "%Y-%m-%d"
    )

    arquivo_log = (
        PASTA_LOGS
        / f"autotube_{data_atual}.log"
    )

    logger = logging.getLogger(
        "autotube"
    )

    logger.setLevel(
        logging.INFO
    )

    logger.propagate = False

    if not logger.handlers:
        formato = logging.Formatter(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        arquivo_handler = logging.FileHandler(
            arquivo_log,
            encoding="utf-8",
        )

        arquivo_handler.setFormatter(
            formato
        )

        logger.addHandler(
            arquivo_handler
        )

    _logger = logger

    return _logger
