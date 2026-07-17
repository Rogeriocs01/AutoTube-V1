from pathlib import Path

from googleapiclient.discovery import build

from config import (EXTENSOES_VIDEO, PASTA_PENDENTES_ID, PASTA_PUBLICADOS_ID, PASTA_TEMP,)
from core.auth import obter_credenciais_drive
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from config import EXTENSOES_VIDEO, PASTA_PENDENTES_ID, PASTA_TEMP


def conectar_drive():
    credenciais = obter_credenciais_drive()

    if credenciais is None:
        return None

    return build(
        "drive",
        "v3",
        credentials=credenciais,
    )


def testar_conexao_drive():
    service = conectar_drive()

    if service is None:
        print("Não foi possível conectar ao Google Drive.")
        return False

    print("Conectado ao Google Drive com sucesso!")
    return True


def listar_videos_pendentes():
    service = conectar_drive()

    if service is None:
        return []

    query = (
        f"'{PASTA_PENDENTES_ID}' in parents "
        "and trashed = false"
    )

    videos = []
    page_token = None

    while True:
        resultado = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, size)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        for arquivo in resultado.get("files", []):
            extensao = Path(arquivo["name"]).suffix.lower()

            if extensao in EXTENSOES_VIDEO:
                videos.append(arquivo)

        page_token = resultado.get("nextPageToken")

        if not page_token:
            break

    return sorted(
        videos,
        key=lambda arquivo: arquivo["name"].lower(),
    )


def mostrar_videos_pendentes():
    videos = listar_videos_pendentes()

    print(f"\nVídeos encontrados: {len(videos)}")

    for video in videos:
        print(f"- {video['name']}")

def baixar_video(drive_id, nome_arquivo):
    service = conectar_drive()

    if service is None:
        print("Não foi possível conectar ao Google Drive.")
        return None

    PASTA_TEMP.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Impede que um nome vindo do Drive crie caminhos fora de temp.
    nome_seguro = Path(nome_arquivo).name
    caminho_destino = PASTA_TEMP / nome_seguro

    if caminho_destino.exists():
        print("\nO vídeo já está na pasta temporária:")
        print(caminho_destino)
        return caminho_destino

    try:
        requisicao = service.files().get_media(
            fileId=drive_id
        )

        with caminho_destino.open("wb") as arquivo_local:
            downloader = MediaIoBaseDownload(
                arquivo_local,
                requisicao,
            )

            concluido = False

            while not concluido:
                progresso, concluido = downloader.next_chunk()

                if progresso:
                    percentual = int(progresso.progress() * 100)

                    print(
                        f"\rBaixando: {percentual}%",
                        end="",
                        flush=True,
                    )

        print("\nDownload concluído:")
        print(caminho_destino)

        return caminho_destino

    except HttpError as erro:
        print(f"\nErro ao baixar o vídeo do Drive: {erro}")

    except OSError as erro:
        print(f"\nErro ao salvar o vídeo no computador: {erro}")

    # Remove arquivo incompleto, caso o download tenha falhado.
    if caminho_destino.exists():
        caminho_destino.unlink()

    return None        

def mover_video_para_publicados(drive_id):
    service = conectar_drive()

    if service is None:
        print("Não foi possível conectar ao Google Drive.")
        return False

    try:
        service.files().update(
            fileId=drive_id,
            addParents=PASTA_PUBLICADOS_ID,
            removeParents=PASTA_PENDENTES_ID,
            fields="id, parents",
        ).execute()

        print("Vídeo movido para a pasta Publicados.")
        return True

    except HttpError as erro:
        print(f"Erro ao mover o vídeo no Google Drive: {erro}")
        return False