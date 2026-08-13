import json

from core.projetos import (
    obter_arquivo_metadados_projeto,
)


def carregar_arquivo_metadados():
    """
    Carrega o arquivo metadados.json
    pertencente ao projeto ativo.
    """

    caminho_metadados = (
        obter_arquivo_metadados_projeto()
    )

    if not caminho_metadados.exists():
        print(
            "\nArquivo de metadados "
            "não encontrado:"
            f"\n{caminho_metadados}"
        )
        return {}

    try:
        conteudo = (
            caminho_metadados.read_text(
                encoding="utf-8"
            ).strip()
        )

        if not conteudo:
            return {}

        dados = json.loads(conteudo)

        if not isinstance(dados, dict):
            print(
                "\nO arquivo metadados.json "
                "possui um formato inválido."
            )
            return {}

        return dados

    except json.JSONDecodeError as erro:
        print(
            "\nNão foi possível interpretar "
            "o arquivo metadados.json."
        )
        print(f"Detalhes: {erro}")
        return {}

    except OSError as erro:
        print(
            "\nNão foi possível ler "
            "o metadados.json."
        )
        print(f"Detalhes: {erro}")
        return {}


def montar_descricao(
    descricao,
    hashtags,
):
    """
    Junta descrição e hashtags sem
    duplicar as hashtags.
    """

    descricao = str(
        descricao or ""
    ).strip()

    hashtags = str(
        hashtags or ""
    ).strip()

    if not hashtags:
        return descricao

    if hashtags in descricao:
        return descricao

    if not descricao:
        return hashtags

    return (
        f"{descricao}\n\n{hashtags}"
    )


def buscar_metadados(nome_arquivo):
    """
    Procura os metadados pelo nome
    exato do arquivo dentro do
    projeto atualmente selecionado.
    """

    nome_arquivo = str(
        nome_arquivo
    ).strip()

    if not nome_arquivo:
        print(
            "\nNome do arquivo do vídeo "
            "não informado."
        )
        return None

    todos_metadados = (
        carregar_arquivo_metadados()
    )

    metadados = todos_metadados.get(
        nome_arquivo
    )

    if metadados is None:
        print(
            "\n===== METADADOS "
            "NÃO ENCONTRADOS ====="
        )
        print(f"Arquivo: {nome_arquivo}")
        print("")
        print(
            "Cadastre os metadados "
            "antes de publicar:"
        )
        print(
            r"python ferramentas"
            r"\gerenciar_metadados.py"
        )
        print(
            "====================================="
        )

        return None

    if not isinstance(
        metadados,
        dict,
    ):
        print(
            "\nOs metadados encontrados "
            "são inválidos."
        )
        print(f"Arquivo: {nome_arquivo}")
        return None

    status = str(
        metadados.get(
            "status",
            "",
        )
    ).strip().lower()

    if status and status != "pronto":
        print(
            "\nOs metadados ainda "
            "não estão prontos."
        )
        print(f"Arquivo: {nome_arquivo}")
        print(f"Status atual: {status}")
        return None

    titulo = str(
        metadados.get(
            "titulo",
            "",
        )
    ).strip()

    descricao = str(
        metadados.get(
            "descricao",
            "",
        )
    ).strip()

    hashtags = str(
        metadados.get(
            "hashtags",
            "",
        )
    ).strip()

    if not titulo:
        print(
            "\nO título dos metadados "
            "está vazio."
        )
        print(f"Arquivo: {nome_arquivo}")
        return None

    descricao_completa = montar_descricao(
        descricao=descricao,
        hashtags=hashtags,
    )

    return {
        "titulo": titulo,
        "descricao": descricao_completa,
        "hashtags": hashtags,
    }