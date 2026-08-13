from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from config import (
    EXTENSOES_VIDEO,
    PASTA_TEMP,
)

from core.auth import obter_credenciais_drive
from core.projetos import obter_projeto_ativo


def conectar_drive():
    credenciais = obter_credenciais_drive()

    if credenciais is None:
        return None

    return build(
        "drive",
        "v3",
        credentials=credenciais,
    )


def obter_configuracao_drive():
    projeto = obter_projeto_ativo()

    if projeto is None:
        print("\nNenhum projeto ativo foi encontrado.")
        return None

    configuracao_drive = projeto.get("drive", {})

    pasta_pendentes_id = configuracao_drive.get(
        "pasta_pendentes_id"
    )

    pasta_publicados_id = configuracao_drive.get(
        "pasta_publicados_id"
    )

    if not pasta_pendentes_id:
        print(
            "\nO projeto ativo não possui "
            "pasta de Pendentes configurada."
        )
        return None

    if not pasta_publicados_id:
        print(
            "\nO projeto ativo não possui "
            "pasta de Publicados configurada."
        )
        return None

    return {
        "pasta_pendentes_id": pasta_pendentes_id,
        "pasta_publicados_id": pasta_publicados_id,
    }


def testar_conexao_drive():
    service = conectar_drive()

    if service is None:
        print(
            "Não foi possível conectar "
            "ao Google Drive."
        )
        return False

    projeto = obter_projeto_ativo()

    if projeto:
        print(
            f"Projeto ativo: {projeto['nome']}"
        )

    print(
        "Conectado ao Google Drive "
        "com sucesso!"
    )

    return True


def listar_videos_pendentes():
    configuracao = obter_configuracao_drive()

    if configuracao is None:
        return []

    service = conectar_drive()

    if service is None:
        return []

    pasta_pendentes_id = configuracao[
        "pasta_pendentes_id"
    ]

    query = (
        f"'{pasta_pendentes_id}' in parents "
        "and trashed = false"
    )

    videos = []
    page_token = None

    while True:
        resultado = service.files().list(
            q=query,
            fields=(
                "nextPageToken, "
                "files(id, name, mimeType, size)"
            ),
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        for arquivo in resultado.get(
            "files",
            [],
        ):
            extensao = Path(
                arquivo["name"]
            ).suffix.lower()

            if extensao in EXTENSOES_VIDEO:
                videos.append(arquivo)

        page_token = resultado.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return sorted(
        videos,
        key=lambda arquivo: (
            arquivo["name"].lower()
        ),
    )


def mostrar_videos_pendentes():
    projeto = obter_projeto_ativo()

    if projeto:
        print(
            f"\nProjeto ativo: "
            f"{projeto['nome']}"
        )

    videos = listar_videos_pendentes()

    print(
        f"\nVídeos encontrados: {len(videos)}"
    )

    for video in videos:
        print(
            f"- {video['name']}"
        )


def baixar_video(
    drive_id,
    nome_arquivo,
):
    service = conectar_drive()

    if service is None:
        print(
            "Não foi possível conectar "
            "ao Google Drive."
        )
        return None

    PASTA_TEMP.mkdir(
        parents=True,
        exist_ok=True,
    )

    nome_seguro = Path(
        nome_arquivo
    ).name

    caminho_destino = (
        PASTA_TEMP / nome_seguro
    )

    if caminho_destino.exists():
        print(
            "\nO vídeo já está "
            "na pasta temporária:"
        )
        print(
            caminho_destino
        )
        return caminho_destino

    try:
        requisicao = service.files().get_media(
            fileId=drive_id
        )

        with caminho_destino.open(
            "wb"
        ) as arquivo_local:
            downloader = MediaIoBaseDownload(
                arquivo_local,
                requisicao,
            )

            concluido = False

            while not concluido:
                progresso, concluido = (
                    downloader.next_chunk()
                )

                if progresso:
                    percentual = int(
                        progresso.progress() * 100
                    )

                    print(
                        f"\rBaixando: "
                        f"{percentual}%",
                        end="",
                        flush=True,
                    )

        print(
            "\nDownload concluído:"
        )
        print(
            caminho_destino
        )

        return caminho_destino

    except HttpError as erro:
        print(
            "\nErro ao baixar o vídeo "
            f"do Drive: {erro}"
        )

    except OSError as erro:
        print(
            "\nErro ao salvar o vídeo "
            f"no computador: {erro}"
        )

    if caminho_destino.exists():
        caminho_destino.unlink()

    return None


def mover_video_para_publicados(
    drive_id,
):
    configuracao = obter_configuracao_drive()

    if configuracao is None:
        return False

    service = conectar_drive()

    if service is None:
        print(
            "Não foi possível conectar "
            "ao Google Drive."
        )
        return False

    pasta_pendentes_id = configuracao[
        "pasta_pendentes_id"
    ]

    pasta_publicados_id = configuracao[
        "pasta_publicados_id"
    ]

    try:
        service.files().update(
            fileId=drive_id,
            addParents=pasta_publicados_id,
            removeParents=pasta_pendentes_id,
            fields="id, parents",
        ).execute()

        print(
            "Vídeo movido para "
            "a pasta Publicados."
        )

        return True

    except HttpError as erro:
        print(
            "Erro ao mover o vídeo "
            f"no Google Drive: {erro}"
        )
        return False