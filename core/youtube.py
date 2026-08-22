from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from core.auth import obter_credenciais_youtube
from core.projetos import obter_projeto_ativo


def obter_configuracao_youtube():
    projeto = obter_projeto_ativo()

    if projeto is None:
        print(
            "\nNenhum projeto ativo."
        )
        return None

    plataformas = projeto.get(
        "plataformas",
        {},
    )

    youtube = plataformas.get(
        "youtube",
        {},
    )

    if not youtube:
        print(
            "\nO projeto ativo não possui "
            "configuração do YouTube."
        )
        return None

    if not youtube.get("ativo", False):
        print(
            "\nO YouTube está desativado "
            "para este projeto."
        )
        return None

    return youtube


def conectar_youtube():
    configuracao = (
        obter_configuracao_youtube()
    )

    if configuracao is None:
        return None

    credenciais = (
        obter_credenciais_youtube()
    )

    if credenciais is None:
        return None

    return build(
        "youtube",
        "v3",
        credentials=credenciais,
    )


def listar_canais_youtube():
    projeto = obter_projeto_ativo()

    configuracao = (
        obter_configuracao_youtube()
    )

    if configuracao is None:
        return

    youtube = conectar_youtube()

    if youtube is None:
        print(
            "Não foi possível conectar "
            "ao YouTube."
        )
        return

    try:
        resposta = youtube.channels().list(
            part="snippet,id",
            mine=True,
        ).execute()

    except HttpError as erro:
        print(
            "Erro ao consultar os canais "
            f"do YouTube: {erro}"
        )
        return

    canais = resposta.get(
        "items",
        [],
    )

    print(
        "\n===== CANAIS DISPONÍVEIS "
        "NA API ====="
    )

    if projeto:
        print(
            f"Projeto ativo: "
            f"{projeto['nome']}"
        )

    canal_configurado = configuracao.get(
        "canal_id",
        "",
    )

    if not canais:
        print(
            "Nenhum canal encontrado."
        )
        return

    for canal in canais:
        canal_id = canal["id"]
        nome = canal["snippet"]["title"]

        print(
            f"\nNome: {nome}"
        )

        print(
            f"ID: {canal_id}"
        )

        if canal_id == canal_configurado:
            print(
                "Canal configurado: SIM"
            )

        else:
            print(
                "Canal configurado: NÃO"
            )

        print(
            "-" * 40
        )


def validar_canal_youtube():
    configuracao = (
        obter_configuracao_youtube()
    )

    if configuracao is None:
        return False

    canal_configurado = configuracao.get(
        "canal_id"
    )

    if not canal_configurado:
        print(
            "\nNenhum canal_id foi "
            "configurado no projeto."
        )
        return False

    youtube = conectar_youtube()

    if youtube is None:
        return False

    try:
        resposta = youtube.channels().list(
            part="snippet,id",
            mine=True,
        ).execute()

    except HttpError as erro:
        print(
            "\nErro ao validar canal "
            f"do YouTube: {erro}"
        )
        return False

    canais = resposta.get(
        "items",
        [],
    )

    for canal in canais:
        if canal["id"] == canal_configurado:
            print(
                "\nCanal do YouTube validado:"
            )

            print(
                canal["snippet"]["title"]
            )

            return True

    print(
        "\nATENÇÃO!"
    )

    print(
        "A conta autenticada não "
        "corresponde ao canal configurado "
        "para o projeto ativo."
    )

    return False


def publicar_video(
    caminho_video: Path,
    titulo: str,
    descricao: str = "",
    privacidade: str | None = None,
):
    if not caminho_video.exists():
        print(
            f"\nArquivo não encontrado: "
            f"{caminho_video}"
        )
        return None

    configuracao = (
        obter_configuracao_youtube()
    )

    if configuracao is None:
        return None

    if not validar_canal_youtube():
        print(
            "\nUpload cancelado por segurança."
        )
        return None

    youtube = conectar_youtube()

    if youtube is None:
        print(
            "\nNão foi possível conectar "
            "ao YouTube."
        )
        return None

    categoria_id = str(
        configuracao.get(
            "categoria_id",
            "22",
        )
    )

    if privacidade is None:
        privacidade = configuracao.get(
            "privacidade_padrao",
            "private",
        )

    corpo = {
        "snippet": {
            "title": titulo,
            "description": descricao,
            "categoryId": categoria_id,
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

        print(
            "\nEnviando vídeo "
            "para o YouTube..."
        )

        while resposta is None:
            progresso, resposta = (
                requisicao.next_chunk()
            )

            if progresso:
                percentual = int(
                    progresso.progress() * 100
                )

                print(
                    f"\rUpload: "
                    f"{percentual}%",
                    end="",
                    flush=True,
                )

        print(
            "\nUpload concluído "
            "com sucesso!"
        )

        print(
            f"YouTube ID: "
            f"{resposta['id']}"
        )

        print(
            f"Privacidade: "
            f"{privacidade}"
        )

        return resposta["id"]

    except HttpError as erro:
        print(
            f"\nErro da API "
            f"do YouTube: {erro}"
        )

        return None

    except OSError as erro:
        print(
            f"\nErro ao ler "
            f"o arquivo local: {erro}"
        )

        return None

def listar_playlists_youtube():
    projeto = obter_projeto_ativo()

    youtube = conectar_youtube()

    if youtube is None:
        print(
            "\nNão foi possível conectar "
            "ao YouTube."
        )
        return []

    playlists = []
    page_token = None

    try:
        while True:
            resposta = youtube.playlists().list(
                part="snippet,id",
                mine=True,
                maxResults=50,
                pageToken=page_token,
            ).execute()

            for item in resposta.get(
                "items",
                [],
            ):
                playlists.append(
                    {
                        "id": item["id"],
                        "nome": (
                            item["snippet"]["title"]
                        ),
                    }
                )

            page_token = resposta.get(
                "nextPageToken"
            )

            if not page_token:
                break

    except HttpError as erro:
        print(
            "\nErro ao consultar playlists "
            f"do YouTube: {erro}"
        )
        return []

    print(
        "\n===== PLAYLISTS DO YOUTUBE ====="
    )

    if projeto:
        print(
            f"Projeto ativo: "
            f"{projeto['nome']}"
        )

    if not playlists:
        print(
            "\nNenhuma playlist encontrada."
        )
        return []

    for indice, playlist in enumerate(
        playlists,
        start=1,
    ):
        print(
            f"\n{indice} - "
            f"{playlist['nome']}"
        )

        print(
            f"ID: {playlist['id']}"
        )

    print(
        "\n================================"
    )

    return playlists

def adicionar_video_playlist(
    youtube_id: str,
    playlist_id: str,
):
    if not playlist_id:
        print(
            "\nNenhuma playlist definida. "
            "Etapa ignorada."
        )
        return True

    youtube = conectar_youtube()

    if youtube is None:
        print(
            "\nNão foi possível conectar "
            "ao YouTube para adicionar "
            "o vídeo à playlist."
        )
        return False

    corpo = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": youtube_id,
            },
        }
    }

    try:
        youtube.playlistItems().insert(
            part="snippet",
            body=corpo,
        ).execute()

        print(
            "\nVídeo adicionado à playlist "
            "com sucesso."
        )

        return True

    except HttpError as erro:
        print(
            "\nO vídeo foi publicado, "
            "mas não foi possível adicioná-lo "
            "à playlist."
        )

        print(
            f"Detalhes: {erro}"
        )

        return False

def definir_thumbnail_youtube(
    youtube_id: str,
    caminho_thumbnail: Path,
):
    if caminho_thumbnail is None:
        print(
            "\nNenhuma thumbnail definida. "
            "Etapa ignorada."
        )
        return True

    if not caminho_thumbnail.exists():
        print(
            "\nArquivo de thumbnail "
            "não encontrado:"
        )
        print(caminho_thumbnail)
        return False

    extensao = (
        caminho_thumbnail.suffix.lower()
    )

    if extensao in {
        ".jpg",
        ".jpeg",
    }:
        mimetype = "image/jpeg"

    elif extensao == ".png":
        mimetype = "image/png"

    else:
        print(
            "\nFormato de thumbnail "
            "não suportado."
        )
        print(
            "Use JPG, JPEG ou PNG."
        )
        return False

    youtube = conectar_youtube()

    if youtube is None:
        print(
            "\nNão foi possível conectar "
            "ao YouTube para enviar "
            "a thumbnail."
        )
        return False

    midia = MediaFileUpload(
        str(caminho_thumbnail),
        mimetype=mimetype,
        resumable=False,
    )

    try:
        youtube.thumbnails().set(
            videoId=youtube_id,
            media_body=midia,
        ).execute()

        print(
            "\nThumbnail definida "
            "com sucesso."
        )

        return True

    except HttpError as erro:
        print(
            "\nO vídeo foi publicado, "
            "mas não foi possível definir "
            "a thumbnail."
        )

        print(
            f"Detalhes: {erro}"
        )

        return False

def obter_canal_youtube_autenticado():
    configuracao = obter_configuracao_youtube()

    if configuracao is None:
        return None

    canal_configurado = configuracao.get(
        "canal_id",
        "",
    )

    youtube = conectar_youtube()

    if youtube is None:
        return None

    try:
        resposta = youtube.channels().list(
            part="snippet,id",
            mine=True,
        ).execute()

    except HttpError as erro:
        print(
            "\nErro ao identificar o canal "
            f"do YouTube: {erro}"
        )
        return None

    for canal in resposta.get(
        "items",
        [],
    ):
        if canal["id"] == canal_configurado:
            return {
                "id": canal["id"],
                "nome": canal["snippet"]["title"],
            }

    return None