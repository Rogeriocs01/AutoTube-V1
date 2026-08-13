import json
from pathlib import Path

from config import BASE_DIR


PASTA_PROJETOS = BASE_DIR / "projetos"
ARQUIVO_PROJETOS = PASTA_PROJETOS / "projetos.json"
ARQUIVO_PROJETO_ATIVO = PASTA_PROJETOS / "projeto_ativo.json"


def garantir_estrutura_projetos():
    PASTA_PROJETOS.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not ARQUIVO_PROJETOS.exists():
        ARQUIVO_PROJETOS.write_text(
            "{}",
            encoding="utf-8",
        )


def carregar_projetos():
    garantir_estrutura_projetos()

    try:
        conteudo = ARQUIVO_PROJETOS.read_text(
            encoding="utf-8"
        )

        if not conteudo.strip():
            return {}

        return json.loads(conteudo)

    except (json.JSONDecodeError, OSError) as erro:
        print(
            f"\nErro ao carregar projetos: {erro}"
        )
        return {}


def salvar_projetos(projetos):
    garantir_estrutura_projetos()

    try:
        ARQUIVO_PROJETOS.write_text(
            json.dumps(
                projetos,
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
        )

        return True

    except OSError as erro:
        print(
            f"\nErro ao salvar projetos: {erro}"
        )
        return False


def listar_projetos():
    projetos = carregar_projetos()

    print("\n===== PROJETOS CADASTRADOS =====")

    if not projetos:
        print("Nenhum projeto cadastrado.")
        return

    projeto_ativo_id = obter_projeto_ativo_id()

    for projeto_id, dados in projetos.items():
        marcador = ""

        if projeto_id == projeto_ativo_id:
            marcador = "  <-- ATIVO"

        print(
            f"{projeto_id} - "
            f"{dados.get('nome', 'Sem nome')}"
            f"{marcador}"
        )


def salvar_projeto_ativo(projeto_id):
    garantir_estrutura_projetos()

    dados = {
        "projeto_id": projeto_id
    }

    try:
        ARQUIVO_PROJETO_ATIVO.write_text(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
        )

        return True

    except OSError as erro:
        print(
            f"\nErro ao salvar projeto ativo: {erro}"
        )
        return False


def obter_projeto_ativo_id():
    garantir_estrutura_projetos()

    if ARQUIVO_PROJETO_ATIVO.exists():
        try:
            dados = json.loads(
                ARQUIVO_PROJETO_ATIVO.read_text(
                    encoding="utf-8"
                )
            )

            projeto_id = dados.get("projeto_id")

            if projeto_id:
                return projeto_id

        except (json.JSONDecodeError, OSError):
            pass

    projetos = carregar_projetos()

    for projeto_id, dados in projetos.items():
        if dados.get("ativo", False):
            salvar_projeto_ativo(projeto_id)
            return projeto_id

    if projetos:
        primeiro_id = next(iter(projetos))
        salvar_projeto_ativo(primeiro_id)
        return primeiro_id

    return None


def obter_projeto_ativo():
    projetos = carregar_projetos()
    projeto_id = obter_projeto_ativo_id()

    if not projeto_id:
        return None

    projeto = projetos.get(projeto_id)

    if projeto is None:
        return None

    return {
        "id": projeto_id,
        **projeto,
    }


def mostrar_projeto_ativo():
    projeto = obter_projeto_ativo()

    if projeto is None:
        print("\nNenhum projeto ativo.")
        return

    print("\n===== PROJETO ATIVO =====")
    print(f"ID: {projeto['id']}")
    print(f"Nome: {projeto['nome']}")

    plataformas = projeto.get(
        "plataformas",
        {}
    )

    youtube = plataformas.get(
        "youtube",
        {}
    )

    if youtube.get("ativo"):
        print("YouTube: ATIVO")
    else:
        print("YouTube: INATIVO")


def selecionar_projeto():
    projetos = carregar_projetos()

    if not projetos:
        print("\nNenhum projeto cadastrado.")
        return

    lista_ids = list(projetos.keys())

    print("\n===== SELECIONAR PROJETO =====")

    for indice, projeto_id in enumerate(
        lista_ids,
        start=1,
    ):
        nome = projetos[projeto_id].get(
            "nome",
            "Sem nome",
        )

        print(
            f"{indice} - {nome}"
        )

    escolha = input(
        "\nEscolha o projeto: "
    ).strip()

    if not escolha.isdigit():
        print("\nOpção inválida.")
        return

    indice = int(escolha) - 1

    if indice < 0 or indice >= len(lista_ids):
        print("\nOpção inválida.")
        return

    projeto_id = lista_ids[indice]

    if salvar_projeto_ativo(projeto_id):
        nome = projetos[projeto_id]["nome"]

        print(
            f"\nProjeto ativo alterado para: "
            f"{nome}"
        )

def obter_pasta_dados_projeto():
    projeto_id = obter_projeto_ativo_id()

    if not projeto_id:
        raise RuntimeError(
            "Nenhum projeto ativo foi definido."
        )

    pasta = BASE_DIR / "dados" / projeto_id

    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )

    return pasta


def obter_arquivo_controle_projeto():
    pasta = obter_pasta_dados_projeto()

    return pasta / "videos.json"


def obter_arquivo_metadados_projeto():
    pasta = obter_pasta_dados_projeto()

    return pasta / "metadados.json"

def obter_pasta_credenciais_projeto():
    projeto_id = obter_projeto_ativo_id()

    if not projeto_id:
        raise RuntimeError(
            "Nenhum projeto ativo foi definido."
        )

    pasta = (
        BASE_DIR
        / "credenciais"
        / projeto_id
    )

    pasta.mkdir(
        parents=True,
        exist_ok=True,
    )

    return pasta


def obter_token_youtube_projeto():
    pasta = obter_pasta_credenciais_projeto()

    return pasta / "token_youtube.json"