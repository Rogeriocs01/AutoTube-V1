import json
from pathlib import Path


CAMINHO_METADADOS = (
    Path(__file__).resolve().parent.parent
    / "dados"
    / "metadados.json"
)


def carregar_arquivo_metadados():
    """
    Carrega o conteúdo do arquivo dados/metadados.json.

    Retorna um dicionário vazio caso o arquivo não exista,
    esteja vazio ou contenha um JSON inválido.
    """
    if not CAMINHO_METADADOS.exists():
        print(
            "\nArquivo de metadados não encontrado:"
            f"\n{CAMINHO_METADADOS}"
        )
        return {}

    try:
        conteudo = CAMINHO_METADADOS.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:
            return {}

        dados = json.loads(conteudo)

        if not isinstance(dados, dict):
            print(
                "\nO arquivo metadados.json possui "
                "um formato inválido."
            )
            return {}

        return dados

    except json.JSONDecodeError as erro:
        print(
            "\nNão foi possível interpretar o "
            "arquivo metadados.json."
        )
        print(f"Detalhes: {erro}")
        return {}

    except OSError as erro:
        print("\nNão foi possível ler o metadados.json.")
        print(f"Detalhes: {erro}")
        return {}


def montar_descricao(descricao, hashtags):
    """
    Junta a descrição e as hashtags.

    Caso as hashtags já estejam presentes na descrição,
    elas não serão adicionadas novamente.
    """
    descricao = str(descricao or "").strip()
    hashtags = str(hashtags or "").strip()

    if not hashtags:
        return descricao

    if hashtags in descricao:
        return descricao

    if not descricao:
        return hashtags

    return f"{descricao}\n\n{hashtags}"


def buscar_metadados(nome_arquivo):
    """
    Procura os metadados de um vídeo pelo nome exato
    do arquivo.

    Exemplo:
    17867470371350431.mp4
    """
    nome_arquivo = str(nome_arquivo).strip()

    if not nome_arquivo:
        print("\nNome do arquivo do vídeo não informado.")
        return None

    todos_metadados = carregar_arquivo_metadados()

    metadados = todos_metadados.get(nome_arquivo)

    if metadados is None:
        print("\n===== METADADOS NÃO ENCONTRADOS =====")
        print(f"Arquivo: {nome_arquivo}")
        print("")
        print(
            "Cadastre os metadados antes de publicar:"
        )
        print(
            r"python ferramentas\gerenciar_metadados.py"
        )
        print("=====================================")
        return None

    if not isinstance(metadados, dict):
        print("\nOs metadados encontrados são inválidos.")
        print(f"Arquivo: {nome_arquivo}")
        return None

    status = str(
        metadados.get("status", "")
    ).strip().lower()

    if status and status != "pronto":
        print("\nOs metadados ainda não estão prontos.")
        print(f"Arquivo: {nome_arquivo}")
        print(f"Status atual: {status}")
        return None

    titulo = str(
        metadados.get("titulo", "")
    ).strip()

    descricao = str(
        metadados.get("descricao", "")
    ).strip()

    hashtags = str(
        metadados.get("hashtags", "")
    ).strip()

    if not titulo:
        print("\nO título dos metadados está vazio.")
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