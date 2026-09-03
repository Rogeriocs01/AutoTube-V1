import json

from config import (
    PASTA_DADOS,
    PASTA_PROJETOS,
)

from core.database import criar_schema

from core.repositorio import (
    salvar_conteudo,
    salvar_metadados,
    salvar_projeto,
)


ARQUIVO_PROJETOS = (
    PASTA_PROJETOS
    / "projetos.json"
)


def carregar_json(caminho):
    """
    Carrega um arquivo JSON.

    Retorna None caso o arquivo
    não exista.
    """

    if not caminho.exists():
        return None

    with caminho.open(
        "r",
        encoding="utf-8-sig",
    ) as arquivo:
        return json.load(arquivo)


def criar_id_global(
    projeto_id,
    id_legado,
):
    """
    Cria o ID global de um conteúdo.

    Exemplo:

    projeto_001 + YT_0001

    torna-se:

    projeto_001:YT_0001
    """

    return (
        f"{projeto_id}:"
        f"{id_legado}"
    )


def normalizar_projetos(dados):
    """
    Normaliza diferentes formatos possíveis
    do arquivo projetos.json.
    """

    if dados is None:
        return []

    if isinstance(dados, list):
        return dados

    if isinstance(dados, dict):
        if isinstance(
            dados.get("projetos"),
            list,
        ):
            return dados["projetos"]

        projetos = []

        for projeto_id, projeto in dados.items():
            if not isinstance(
                projeto,
                dict,
            ):
                continue

            item = dict(projeto)

            item.setdefault(
                "id",
                projeto_id,
            )

            projetos.append(
                item
            )

        return projetos

    return []


def normalizar_videos(dados):
    """
    Normaliza os registros de vídeos.

    O formato atual utiliza normalmente
    o ID legado como chave:

    YT_0004 -> dados do vídeo
    """

    if dados is None:
        return {}

    if isinstance(dados, dict):
        return dados

    if isinstance(dados, list):
        resultado = {}

        for item in dados:
            if not isinstance(
                item,
                dict,
            ):
                continue

            video_id = (
                item.get("id")
                or item.get("video_id")
            )

            if video_id:
                resultado[
                    video_id
                ] = item

        return resultado

    return {}


def normalizar_metadados(dados):
    """
    Normaliza os metadados usando
    o video_id legado como chave.

    Os arquivos atuais do AutoTube
    utilizam normalmente:

    nome_do_arquivo.mp4 -> {
        "video_id": "YT_0004",
        ...
    }

    Esta função transforma isso em:

    YT_0004 -> metadados
    """

    if dados is None:
        return {}

    resultado = {}

    if isinstance(dados, dict):
        for chave, item in dados.items():
            if not isinstance(
                item,
                dict,
            ):
                continue

            video_id = (
                item.get("video_id")
                or item.get("id")
            )

            if not video_id:
                if str(chave).startswith(
                    "YT_"
                ):
                    video_id = chave

            if not video_id:
                continue

            resultado[
                video_id
            ] = item

        return resultado

    if isinstance(dados, list):
        for item in dados:
            if not isinstance(
                item,
                dict,
            ):
                continue

            video_id = (
                item.get("video_id")
                or item.get("id")
            )

            if video_id:
                resultado[
                    video_id
                ] = item

    return resultado


def importar_projetos():
    """
    Importa os projetos atuais.
    """

    dados = carregar_json(
        ARQUIVO_PROJETOS
    )

    projetos = normalizar_projetos(
        dados
    )

    importados = 0

    for projeto in projetos:
        projeto_id = (
            projeto.get("id")
            or projeto.get("projeto_id")
        )

        if not projeto_id:
            continue

        nome = (
            projeto.get("nome")
            or projeto.get("nome_projeto")
            or projeto_id
        )

        salvar_projeto(
            projeto_id=projeto_id,
            nome=nome,
            slug=projeto.get("slug"),
            descricao=projeto.get(
                "descricao"
            ),
            ativo=projeto.get(
                "ativo",
                True,
            ),
        )

        importados += 1

    return importados


def obter_status_conteudo(video):
    """
    Converte o status legado
    para o novo modelo.
    """

    status = str(
        video.get(
            "status",
            "pendente",
        )
    ).upper()

    mapa = {
        "PENDENTE": "PENDENTE",
        "PUBLICADO": "CONCLUIDO",
        "CONCLUIDO": "CONCLUIDO",
        "ERRO": "ERRO",
    }

    return mapa.get(
        status,
        status,
    )


def obter_conteudo_pai_global(
    projeto_id,
    video,
):
    """
    Converte um eventual conteúdo pai
    legado para o ID global.

    Caso não exista relacionamento,
    retorna None.
    """

    conteudo_pai_id = (
        video.get("conteudo_pai_id")
    )

    if not conteudo_pai_id:
        return None

    conteudo_pai_id = str(
        conteudo_pai_id
    )

    if ":" in conteudo_pai_id:
        return conteudo_pai_id

    return criar_id_global(
        projeto_id,
        conteudo_pai_id,
    )


def importar_conteudos_projeto(
    projeto_id,
):
    """
    Importa vídeos e metadados
    de um projeto.

    Cada ID legado é convertido
    para um ID global.
    """

    pasta = (
        PASTA_DADOS
        / projeto_id
    )

    arquivo_videos = (
        pasta
        / "videos.json"
    )

    arquivo_metadados = (
        pasta
        / "metadados.json"
    )

    videos = normalizar_videos(
        carregar_json(
            arquivo_videos
        )
    )

    metadados = normalizar_metadados(
        carregar_json(
            arquivo_metadados
        )
    )

    conteudos_importados = 0
    metadados_importados = 0

    for video_id, video in videos.items():
        if not isinstance(
            video,
            dict,
        ):
            continue

        id_legado = str(
            video_id
        )

        conteudo_id = criar_id_global(
            projeto_id,
            id_legado,
        )

        salvar_conteudo(
            conteudo_id=conteudo_id,
            projeto_id=projeto_id,
            id_legado=id_legado,
            tipo=(
                video.get(
                    "tipo_conteudo"
                )
                or video.get("tipo")
            ),
            nome_arquivo=(
                video.get("arquivo")
                or video.get(
                    "nome_arquivo"
                )
            ),
            origem=video.get(
                "origem",
                "google_drive",
            ),
            conteudo_pai_id=(
                obter_conteudo_pai_global(
                    projeto_id,
                    video,
                )
            ),
            drive_file_id=(
                  video.get("drive_file_id")
                    or video.get("drive_id")
                    or video.get("file_id")
),
        )

        conteudos_importados += 1

        metadata = metadados.get(
            id_legado
        )

        if not isinstance(
            metadata,
            dict,
        ):
            continue

        hashtags = metadata.get(
            "hashtags"
        )

        if isinstance(
            hashtags,
            list,
        ):
            hashtags = " ".join(
                hashtags
            )

        salvar_metadados(
            conteudo_id=conteudo_id,
            titulo=metadata.get(
                "titulo"
            ),
            descricao=metadata.get(
                "descricao"
            ),
            hashtags=hashtags,
            playlist_id=metadata.get(
                "playlist_id"
            ),
            playlist_nome=metadata.get(
                "playlist_nome"
            ),
            idioma=metadata.get(
                "idioma"
            ),
            categoria=metadata.get(
                "categoria"
            ),
        )

        metadados_importados += 1

    return (
        conteudos_importados,
        metadados_importados,
    )


def migrar_tudo():
    """
    Executa a migração inicial
    JSON -> SQLite.

    Os IDs legados permanecem armazenados
    separadamente dos IDs globais.
    """

    criar_schema()

    quantidade_projetos = (
        importar_projetos()
    )

    dados_projetos = carregar_json(
        ARQUIVO_PROJETOS
    )

    projetos = normalizar_projetos(
        dados_projetos
    )

    total_conteudos = 0
    total_metadados = 0

    for projeto in projetos:
        projeto_id = (
            projeto.get("id")
            or projeto.get(
                "projeto_id"
            )
        )

        if not projeto_id:
            continue

        (
            conteudos,
            metadados,
        ) = importar_conteudos_projeto(
            projeto_id
        )

        total_conteudos += (
            conteudos
        )

        total_metadados += (
            metadados
        )

    return {
        "projetos": quantidade_projetos,
        "conteudos": total_conteudos,
        "metadados": total_metadados,
    }