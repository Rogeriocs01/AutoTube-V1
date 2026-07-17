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


# Google Drive
PASTA_PENDENTES_ID = "1gD73Mm3PPW8007G6SwcPu6TCzUdwGGw7"
PASTA_PUBLICADOS_ID = "1uL1wSTRk7viwYesgUJkRbz_FrWE7KQ9v"


# Canal correto do YouTube
CANAL_YOUTUBE_ID = "UCpY6Pi1fPLVmXY19l6SUOlg"


# Pastas locais
PASTA_DADOS = BASE_DIR / "dados"
PASTA_LOGS = BASE_DIR / "logs"
PASTA_TEMP = BASE_DIR / "temp"


# Arquivos locais
ARQUIVO_CONTROLE = PASTA_DADOS / "videos.json"
ARQUIVO_CREDENTIALS = BASE_DIR / "credentials.json"

ARQUIVO_TOKEN_DRIVE = BASE_DIR / "token_drive.json"
ARQUIVO_TOKEN_YOUTUBE = BASE_DIR / "token_youtube.json"


EXTENSOES_VIDEO = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}