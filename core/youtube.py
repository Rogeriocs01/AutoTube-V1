from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import CANAL_YOUTUBE_ID
from core.auth import obter_credenciais_youtube
from pathlib import Path
from googleapiclient.http import MediaFileUpload



def conectar_youtube():
    credenciais = obter_credenciais_youtube()

    if credenciais is None:
        return None

    return build(
        "youtube",
        "v3",
        credentials=credenciais,
    )


def listar_canais_youtube():
    youtube = conectar_youtube()

    if youtube is None:
        print("Não foi possível conectar ao YouTube.")
        return

    try:
        resposta = youtube.channels().list(
            part="snippet,id",
            mine=True,
        ).execute()

    except HttpError as erro:
        print(f"Erro ao consultar os canais do YouTube: {erro}")
        return

    canais = resposta.get("items", [])

    print("\n===== CANAIS DISPONÍVEIS NA API =====")

    if not canais:
        print("Nenhum canal encontrado.")
        return

    for canal in canais:
        canal_id = canal["id"]
        nome = canal["snippet"]["title"]

        print(f"Nome: {nome}")
        print(f"ID: {canal_id}")

        if canal_id == CANAL_YOUTUBE_ID:
            print("Canal configurado: SIM")
        else:
            print("Canal configurado: NÃO")

        print("-" * 40)

def publicar_video(
    caminho_video: Path,
    titulo: str,
    descricao: str = "",
    privacidade: str = "private",
):
    if not caminho_video.exists():
        print(f"\nArquivo não encontrado: {caminho_video}")
        return None

    youtube = conectar_youtube()

    if youtube is None:
        print("\nNão foi possível conectar ao YouTube.")
        return None

    corpo = {
        "snippet": {
            "title": titulo,
            "description": descricao,
            "categoryId": "28",
        },
        "status": {
            "privacyStatus": privacidade,
            "selfDeclaredMadeForKids": False,
        },
    }

    midia = MediaFileUpload(
        str(caminho_video),
        mimetype="video/*",
        chunksize=-1,
        resumable=True,
    )

    try:
        requisicao = youtube.videos().insert(
            part="snippet,status",
            body=corpo,
            media_body=midia,
        )

        resposta = None

        print("\nEnviando vídeo para o YouTube...")

        while resposta is None:
            progresso, resposta = requisicao.next_chunk()

            if progresso:
                percentual = int(progresso.progress() * 100)
                print(
                    f"\rUpload: {percentual}%",
                    end="",
                    flush=True,
                )

        print("\nUpload concluído com sucesso!")
        print(f"YouTube ID: {resposta['id']}")
        print(f"Privacidade: {privacidade}")

        return resposta["id"]

    except HttpError as erro:
        print(f"\nErro da API do YouTube: {erro}")
        return None

    except OSError as erro:
        print(f"\nErro ao ler o arquivo local: {erro}")
        return None        