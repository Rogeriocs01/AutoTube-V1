from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import (
    MediaFileUpload,
    MediaIoBaseDownload,
)

from config import (
    EXTENSOES_VIDEO,
    PASTA_TEMP,
)

from core.auth import obter_credenciais_drive
from core.projetos import obter_projeto_ativo


EXTENSOES_THUMBNAIL = {
    ".jpg",
    ".jpeg",
    ".png",
}


# =========================================================
# CONEXÃO / CONFIGURAÇÃO
# =========================================================

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
        print(
            "\nNenhum projeto ativo foi encontrado."
        )
        return None

    configuracao_drive = projeto.get(
        "drive",
        {},
    )

    pasta_pendentes_id = configuracao_drive.get(
        "pasta_pendentes_id"
    )

    pasta_publicados_id = configuracao_drive.get(
        "pasta_publicados_id"
    )

    pasta_erros_id = configuracao_drive.get(
        "pasta_erros_id",
        "",
    )

    pasta_thumbs_id = configuracao_drive.get(
        "pasta_thumbs_id",
        "",
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
        "pasta_erros_id": pasta_erros_id,
        "pasta_thumbs_id": pasta_thumbs_id,
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


# =========================================================
# VÍDEOS PENDENTES
# =========================================================

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
        try:
            resultado = service.files().list(
                q=query,
                fields=(
                    "nextPageToken, "
                    "files(id, name, mimeType, size)"
                ),
                pageSize=1000,
                pageToken=page_token,
            ).execute()

        except HttpError as erro:
            print(
                "\nErro ao listar vídeos "
                f"do Google Drive: {erro}"
            )
            return []

        for arquivo in resultado.get(
            "files",
            [],
        ):
            extensao = Path(
                arquivo["name"]
            ).suffix.lower()

            if extensao in EXTENSOES_VIDEO:
                videos.append(
                    arquivo
                )

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
        f"\nVídeos encontrados: "
        f"{len(videos)}"
    )

    for video in videos:
        print(
            f"- {video['name']}"
        )


# =========================================================
# DOWNLOAD DE VÍDEO
# =========================================================

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
        requisicao = (
            service.files().get_media(
                fileId=drive_id
            )
        )

        with caminho_destino.open(
            "wb"
        ) as arquivo_local:
            downloader = (
                MediaIoBaseDownload(
                    arquivo_local,
                    requisicao,
                )
            )

            concluido = False

            while not concluido:
                progresso, concluido = (
                    downloader.next_chunk()
                )

                if progresso:
                    percentual = int(
                        progresso.progress()
                        * 100
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


# =========================================================
# THUMBNAILS - BUSCA
# =========================================================

def buscar_thumbnail_drive(
    nome_video,
):
    """
    Procura na pasta Thumbs do projeto ativo
    um arquivo com o mesmo nome-base do vídeo.

    Aceita arquivos:
    - com extensão .jpg/.jpeg/.png
    - sem extensão

    Exemplo:

    vídeo:
        beastofreincarnation01.mp4

    thumbnails aceitas:
        beastofreincarnation01.png
        beastofreincarnation01.jpg
        beastofreincarnation01
    """

    configuracao = obter_configuracao_drive()

    if configuracao is None:
        return None

    pasta_thumbs_id = configuracao.get(
        "pasta_thumbs_id"
    )

    if not pasta_thumbs_id:
        return None

    service = conectar_drive()

    if service is None:
        return None

    nome_base_video = Path(
        nome_video
    ).stem.strip().lower()

    query = (
        f"'{pasta_thumbs_id}' in parents "
        "and trashed = false"
    )

    try:
        resultado = service.files().list(
            q=query,
            fields=(
                "files("
                "id, "
                "name, "
                "mimeType, "
                "size"
                ")"
            ),
            pageSize=1000,
        ).execute()

    except HttpError as erro:
        print(
            "\nErro ao procurar thumbnail "
            f"no Google Drive: {erro}"
        )
        return None

    for arquivo in resultado.get(
        "files",
        [],
    ):
        nome_drive = str(
            arquivo.get(
                "name",
                "",
            )
        ).strip()

        if not nome_drive:
            continue

        caminho = Path(
            nome_drive
        )

        if caminho.suffix:
            nome_base_thumb = (
                caminho.stem
                .strip()
                .lower()
            )

        else:
            nome_base_thumb = (
                nome_drive
                .strip()
                .lower()
            )

        if (
            nome_base_thumb
            == nome_base_video
        ):
            return arquivo

    return None


# =========================================================
# THUMBNAILS - DETECÇÃO DE FORMATO
# =========================================================

def obter_extensao_thumbnail(
    thumbnail,
):
    """
    Determina a extensão correta da thumbnail
    pelo nome ou pelo MIME Type.
    """

    nome = str(
        thumbnail.get(
            "name",
            "",
        )
    )

    extensao = Path(
        nome
    ).suffix.lower()

    if extensao in EXTENSOES_THUMBNAIL:
        return extensao

    mime_type = str(
        thumbnail.get(
            "mimeType",
            "",
        )
    ).lower()

    if mime_type == "image/png":
        return ".png"

    if mime_type in {
        "image/jpeg",
        "image/jpg",
    }:
        return ".jpg"

    return ""


# =========================================================
# THUMBNAILS - DOWNLOAD
# =========================================================

def baixar_thumbnail(
    nome_video,
):
    """
    Procura a thumbnail correspondente
    e baixa para temp/thumbs.

    Caso o arquivo no Drive esteja sem extensão,
    tenta descobrir o formato pelo MIME Type.
    """

    thumbnail = buscar_thumbnail_drive(
        nome_video
    )

    if thumbnail is None:
        return None

    service = conectar_drive()

    if service is None:
        return None

    pasta_temp_thumbs = (
        PASTA_TEMP
        / "thumbs"
    )

    pasta_temp_thumbs.mkdir(
        parents=True,
        exist_ok=True,
    )

    extensao = obter_extensao_thumbnail(
        thumbnail
    )

    if not extensao:
        print(
            "\nThumbnail encontrada, "
            "mas o formato não pôde "
            "ser identificado."
        )

        print(
            f"Nome: "
            f"{thumbnail.get('name', '')}"
        )

        print(
            f"MIME: "
            f"{thumbnail.get('mimeType', '')}"
        )

        return None

    nome_base_video = Path(
        nome_video
    ).stem

    nome_destino = (
        f"{nome_base_video}{extensao}"
    )

    caminho_destino = (
        pasta_temp_thumbs
        / nome_destino
    )

    try:
        requisicao = (
            service.files().get_media(
                fileId=thumbnail["id"]
            )
        )

        with caminho_destino.open(
            "wb"
        ) as arquivo_local:
            downloader = (
                MediaIoBaseDownload(
                    arquivo_local,
                    requisicao,
                )
            )

            concluido = False

            while not concluido:
                _, concluido = (
                    downloader.next_chunk()
                )

        print(
            "\nThumbnail baixada:"
        )

        print(
            caminho_destino
        )

        return caminho_destino

    except HttpError as erro:
        print(
            "\nErro ao baixar thumbnail: "
            f"{erro}"
        )

    except OSError as erro:
        print(
            "\nErro ao salvar thumbnail: "
            f"{erro}"
        )

    if caminho_destino.exists():
        caminho_destino.unlink()

    return None


# =========================================================
# THUMBNAILS - ENVIO PARA O DRIVE
# =========================================================

def enviar_thumbnail_para_drive(
    caminho_thumbnail,
    nome_video,
):
    """
    Envia uma thumbnail local para a pasta
    Thumbs do projeto ativo.

    A thumbnail é automaticamente renomeada
    usando o nome-base do vídeo.
    """

    caminho_thumbnail = Path(
        caminho_thumbnail
    )

    if not caminho_thumbnail.exists():
        print(
            "\nThumbnail local "
            "não encontrada:"
        )
        print(
            caminho_thumbnail
        )
        return None

    extensao = (
        caminho_thumbnail
        .suffix
        .lower()
    )

    if extensao not in EXTENSOES_THUMBNAIL:
        print(
            "\nFormato de thumbnail "
            "inválido."
        )
        print(
            "Use JPG, JPEG ou PNG."
        )
        return None

    configuracao = obter_configuracao_drive()

    if configuracao is None:
        return None

    pasta_thumbs_id = configuracao.get(
        "pasta_thumbs_id"
    )

    if not pasta_thumbs_id:
        print(
            "\nO projeto ativo não possui "
            "pasta Thumbs configurada."
        )
        return None

    service = conectar_drive()

    if service is None:
        return None

    nome_base_video = Path(
        nome_video
    ).stem

    nome_destino = (
        f"{nome_base_video}"
        f"{extensao}"
    )

    corpo = {
        "name": nome_destino,
        "parents": [
            pasta_thumbs_id
        ],
    }

    if extensao in {
        ".jpg",
        ".jpeg",
    }:
        mimetype = "image/jpeg"

    else:
        mimetype = "image/png"

    midia = MediaFileUpload(
        str(caminho_thumbnail),
        mimetype=mimetype,
        resumable=False,
    )

    try:
        arquivo = (
            service.files().create(
                body=corpo,
                media_body=midia,
                fields=(
                    "id, name, mimeType"
                ),
            ).execute()
        )

        print(
            "\nThumbnail enviada "
            "para o Google Drive."
        )

        print(
            f"Nome: "
            f"{arquivo['name']}"
        )

        return arquivo

    except HttpError as erro:
        print(
            "\nErro ao enviar thumbnail "
            f"para o Google Drive: {erro}"
        )

        return None


# =========================================================
# TESTE DE THUMBNAIL
# =========================================================

def testar_thumbnail_video(
    nome_video,
):
    """
    Testa a localização da thumbnail sem
    baixar o vídeo principal.
    """

    projeto = obter_projeto_ativo()
    configuracao = obter_configuracao_drive()

    if configuracao is None:
        return False

    pasta_thumbs_id = configuracao.get(
        "pasta_thumbs_id"
    )

    print(
        "\n========================================"
    )
    print(
        "          TESTE DE THUMBNAIL"
    )
    print(
        "========================================"
    )

    if projeto:
        print(
            f"Projeto       : "
            f"{projeto['nome']}"
        )

    print(
        f"Vídeo         : {nome_video}"
    )

    print(
        f"Nome-base     : "
        f"{Path(nome_video).stem}"
    )

    print(
        f"Pasta Thumbs  : "
        f"{pasta_thumbs_id}"
    )

    if not pasta_thumbs_id:
        print(
            "\nERRO: pasta Thumbs "
            "não configurada."
        )
        return False

    service = conectar_drive()

    if service is None:
        return False

    query = (
        f"'{pasta_thumbs_id}' in parents "
        "and trashed = false"
    )

    try:
        resultado = service.files().list(
            q=query,
            fields=(
                "files("
                "id, "
                "name, "
                "mimeType, "
                "size"
                ")"
            ),
            pageSize=1000,
        ).execute()

    except HttpError as erro:
        print(
            "\nErro ao consultar Thumbs: "
            f"{erro}"
        )
        return False

    arquivos = resultado.get(
        "files",
        [],
    )

    print(
        "\nArquivos encontrados "
        f"na pasta: {len(arquivos)}"
    )

    if not arquivos:
        print(
            "\nA pasta Thumbs está vazia "
            "ou o ID configurado "
            "está incorreto."
        )
        return False

    print(
        "\n===== ARQUIVOS NA PASTA ====="
    )

    for arquivo in arquivos:
        print(
            f"Nome     : "
            f"{arquivo.get('name', '')}"
        )

        print(
            f"MIME     : "
            f"{arquivo.get('mimeType', '')}"
        )

        print(
            f"Drive ID : "
            f"{arquivo.get('id', '')}"
        )

        print(
            "-" * 40
        )

    print(
        "================================"
    )

    thumbnail = buscar_thumbnail_drive(
        nome_video
    )

    if thumbnail is None:
        print(
            "\nRESULTADO: "
            "THUMBNAIL NÃO ENCONTRADA"
        )

        print(
            "\nNome-base procurado:"
        )

        print(
            Path(nome_video).stem
        )

        return False

    print(
        "\nRESULTADO: "
        "THUMBNAIL ENCONTRADA"
    )

    print(
        f"Arquivo : "
        f"{thumbnail.get('name', '')}"
    )

    print(
        f"MIME    : "
        f"{thumbnail.get('mimeType', '')}"
    )

    print(
        f"Drive ID: "
        f"{thumbnail.get('id', '')}"
    )

    extensao = obter_extensao_thumbnail(
        thumbnail
    )

    if extensao:
        print(
            f"Formato : {extensao}"
        )

    else:
        print(
            "Formato : NÃO IDENTIFICADO"
        )

    print(
        "========================================"
    )

    return True


# =========================================================
# MOVER VÍDEO PARA PUBLICADOS
# =========================================================

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