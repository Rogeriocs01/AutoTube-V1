import json
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from core.projetos import (
    obter_arquivo_controle_projeto,
    obter_arquivo_metadados_projeto,
    obter_projeto_ativo,
)

from core.youtube import listar_playlists_youtube


def carregar_json(caminho):
    if not caminho.exists():
        return {}

    try:
        conteudo = caminho.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:
            return {}

        return json.loads(conteudo)

    except (json.JSONDecodeError, OSError) as erro:
        print(
            f"Erro ao ler {caminho.name}: {erro}"
        )
        return {}


def salvar_metadados(metadados):
    arquivo_metadados = (
        obter_arquivo_metadados_projeto()
    )

    arquivo_metadados.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    arquivo_metadados.write_text(
        json.dumps(
            metadados,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def listar_videos_sem_metadados():
    arquivo_videos = (
        obter_arquivo_controle_projeto()
    )

    arquivo_metadados = (
        obter_arquivo_metadados_projeto()
    )

    videos = carregar_json(
        arquivo_videos
    )

    metadados = carregar_json(
        arquivo_metadados
    )

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


def selecionar_playlist():
    print(
        "\nConsultando playlists "
        "do canal ativo..."
    )

    playlists = listar_playlists_youtube()

    if not playlists:
        print(
            "\nNenhuma playlist disponível."
        )

        confirmar = input(
            "Continuar sem playlist? [S/N]: "
        ).strip().lower()

        if confirmar == "s":
            return None

        print(
            "\nCadastro cancelado."
        )
        return "cancelar"

    print(
        "\n0 - Sem playlist"
    )

    while True:
        escolha = input(
            "\nEscolha a playlist: "
        ).strip()

        if escolha == "0":
            return None

        if not escolha.isdigit():
            print(
                "Opção inválida."
            )
            continue

        indice = int(escolha) - 1

        if indice < 0 or indice >= len(playlists):
            print(
                "Opção inválida."
            )
            continue

        return playlists[indice]


def cadastrar_metadados():
    faltantes = listar_videos_sem_metadados()

    if not faltantes:
        print(
            "\nNenhum vídeo pendente "
            "sem metadados."
        )
        return

    proximo = faltantes[0]

    print(
        "\n===== PRÓXIMO VÍDEO "
        "SEM METADADOS ====="
    )

    print(
        f"ID interno : "
        f"{proximo['video_id']}"
    )

    print(
        f"Arquivo    : "
        f"{proximo['arquivo']}"
    )

    print(
        "======================================="
    )

    titulo = input(
        "\nTítulo: "
    ).strip()

    if not titulo:
        print(
            "O título não pode ficar vazio."
        )
        return

    descricao = preencher_descricao()

    hashtags = input(
        "\nHashtags, separadas por espaço: "
    ).strip()

    playlist = selecionar_playlist()

    if playlist == "cancelar":
        return

    arquivo_metadados = (
        obter_arquivo_metadados_projeto()
    )

    metadados = carregar_json(
        arquivo_metadados
    )

    novos_metadados = {
        "video_id": proximo["video_id"],
        "titulo": titulo,
        "descricao": descricao,
        "hashtags": hashtags,
        "status": "pronto",
    }

    if playlist is not None:
        novos_metadados[
            "playlist_id"
        ] = playlist["id"]

        novos_metadados[
            "playlist_nome"
        ] = playlist["nome"]

    else:
        novos_metadados[
            "playlist_id"
        ] = ""

        novos_metadados[
            "playlist_nome"
        ] = ""

    metadados[
        proximo["arquivo"]
    ] = novos_metadados

    salvar_metadados(
        metadados
    )

    print(
        "\nMetadados salvos com sucesso."
    )

    print(
        f"Arquivo: {proximo['arquivo']}"
    )

    if playlist is not None:
        print(
            f"Playlist: "
            f"{playlist['nome']}"
        )

    else:
        print(
            "Playlist: nenhuma"
        )


def mostrar_resumo():
    arquivo_videos = (
        obter_arquivo_controle_projeto()
    )

    arquivo_metadados = (
        obter_arquivo_metadados_projeto()
    )

    videos = carregar_json(
        arquivo_videos
    )

    metadados = carregar_json(
        arquivo_metadados
    )

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

    faltantes = len(
        listar_videos_sem_metadados()
    )

    com_playlist = sum(
        1
        for dados in metadados.values()
        if dados.get("playlist_id")
    )

    print(
        "\n===== RESUMO DOS METADADOS ====="
    )

    print(
        f"Vídeos pendentes : {pendentes}"
    )

    print(
        f"Metadados prontos: {prontos}"
    )

    print(
        f"Sem metadados    : {faltantes}"
    )

    print(
        f"Com playlist     : {com_playlist}"
    )


def mostrar_cabecalho():
    projeto = obter_projeto_ativo()

    print(
        "\n=============================="
    )

    print(
        "   GERENCIADOR DE METADADOS"
    )

    print(
        "=============================="
    )

    if projeto:
        print(
            f"Projeto ativo: {projeto['nome']}"
        )
    else:
        print(
            "Projeto ativo: NENHUM"
        )


def iniciar():
    while True:
        mostrar_cabecalho()

        print(
            "1 - Cadastrar próximo vídeo"
        )

        print(
            "2 - Ver resumo"
        )

        print(
            "0 - Sair"
        )

        opcao = input(
            "\nEscolha uma opção: "
        ).strip()

        if opcao == "1":
            cadastrar_metadados()

        elif opcao == "2":
            mostrar_resumo()

        elif opcao == "0":
            print(
                "Saindo..."
            )
            break

        else:
            print(
                "Opção inválida."
            )


if __name__ == "__main__":
    iniciar()