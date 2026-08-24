from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


# Permissões do Google Drive
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
]


# Permissões do YouTube
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


# Pastas locais
PASTA_DADOS = BASE_DIR / "dados"
PASTA_LOGS = BASE_DIR / "logs"
PASTA_TEMP = BASE_DIR / "temp"


# Credenciais e tokens
ARQUIVO_CREDENTIALS = (
    BASE_DIR / "credentials.json"
)

ARQUIVO_TOKEN_DRIVE = (
    BASE_DIR / "token_drive.json"
)

ARQUIVO_TOKEN_YOUTUBE = (
    BASE_DIR / "token_youtube.json"
)


# Extensões de vídeo aceitas
EXTENSOES_VIDEO = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}