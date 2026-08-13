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