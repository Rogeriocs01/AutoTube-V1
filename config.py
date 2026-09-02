from pathlib import Path
import sys


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent


PASTA_AUTOTUBE_DATA = (
    BASE_DIR.parent
    / "AutoTube Data"
)

PASTA_DADOS = (
    PASTA_AUTOTUBE_DATA
    / "dados"
)

PASTA_PROJETOS = (
    PASTA_AUTOTUBE_DATA
    / "projetos"
)


PASTA_LOGS = (
    BASE_DIR
    / "logs"
)

PASTA_TEMP = (
    BASE_DIR
    / "temp"
)


DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


ARQUIVO_CREDENTIALS = (
    BASE_DIR
    / "credentials.json"
)

ARQUIVO_TOKEN_DRIVE = (
    BASE_DIR
    / "token_drive.json"
)

ARQUIVO_TOKEN_YOUTUBE = (
    BASE_DIR
    / "token_youtube.json"
)


EXTENSOES_VIDEO = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}
