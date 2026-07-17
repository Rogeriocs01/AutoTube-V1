import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_VIDEOS = BASE_DIR / "dados" / "videos.json"
ARQUIVO_METADADOS = BASE_DIR / "dados" / "metadados.json"


def carregar_json(caminho):
    if not caminho.exists():
        return {}

    try:
        conteudo = caminho.read_text(encoding="utf-8").strip()

        if not conteudo:
            return {}

        return json.loads(conteudo)

    except (json.JSONDecodeError, OSError) as erro:
        print(f"Erro ao ler {caminho.name}: {erro}")
        return {}


def salvar_metadados(metadados):
    ARQUIVO_METADADOS.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARQUIVO_METADADOS.write_text(
        json.dumps(
            metadados,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def listar_videos_sem_metadados():
    videos = carregar_json(ARQUIVO_VIDEOS)
    metadados = carregar_json(ARQUIVO_METADADOS)

    faltantes = []

    for video_id, video in videos.items():
        arquivo = video.get("arquivo")

        if (
            arquivo
            and video.get("status") == "pendente"
            and arquivo not in metadados
        ):
            faltantes.append(
                {
                    "video_id": video_id,
                    "arquivo": arquivo,
                }
            )

    return faltantes


def preencher_descricao():
    print(
        "\nDigite a descrição. "
        "Finalize com uma linha vazia:"
    )

    linhas = []

    while True:
        linha = input()

        if not linha:
            break

        linhas.append(linha)

    return "\n".join(linhas).strip()


def cadastrar_metadados():
    faltantes = listar_videos_sem_metadados()

    if not faltantes:
        print("\nNenhum vídeo pendente sem metadados.")
        return

    proximo = faltantes[0]

    print("\n===== PRÓXIMO VÍDEO SEM METADADOS =====")
    print(f"ID interno : {proximo['video_id']}")
    print(f"Arquivo    : {proximo['arquivo']}")
    print("=======================================")

    titulo = input("\nTítulo: ").strip()

    if not titulo:
        print("O título não pode ficar vazio.")
        return

    descricao = preencher_descricao()

    hashtags = input(
        "\nHashtags, separadas por espaço: "
    ).strip()

    metadados = carregar_json(ARQUIVO_METADADOS)

    metadados[proximo["arquivo"]] = {
        "video_id": proximo["video_id"],
        "titulo": titulo,
        "descricao": descricao,
        "hashtags": hashtags,
        "status": "pronto",
    }

    salvar_metadados(metadados)

    print("\nMetadados salvos com sucesso.")
    print(f"Arquivo: {proximo['arquivo']}")


def mostrar_resumo():
    videos = carregar_json(ARQUIVO_VIDEOS)
    metadados = carregar_json(ARQUIVO_METADADOS)

    pendentes = sum(
        1
        for video in videos.values()
        if video.get("status") == "pendente"
    )

    prontos = sum(
        1
        for dados in metadados.values()
        if dados.get("status") == "pronto"
    )

    faltantes = len(listar_videos_sem_metadados())

    print("\n===== RESUMO DOS METADADOS =====")
    print(f"Vídeos pendentes : {pendentes}")
    print(f"Metadados prontos: {prontos}")
    print(f"Sem metadados    : {faltantes}")


def iniciar():
    while True:
        print("\n==============================")
        print("   GERENCIADOR DE METADADOS")
        print("==============================")
        print("1 - Cadastrar próximo vídeo")
        print("2 - Ver resumo")
        print("0 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            cadastrar_metadados()

        elif opcao == "2":
            mostrar_resumo()

        elif opcao == "0":
            print("Saindo...")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    iniciar()