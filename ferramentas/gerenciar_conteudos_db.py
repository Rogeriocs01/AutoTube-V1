import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from core.drive import buscar_thumbnail_drive
from core.projetos import obter_projeto_ativo
from core.repositorio import (
    listar_conteudos,
    obter_metadados,
    salvar_metadados,
)
from core.youtube import listar_playlists_youtube


def obter_id_projeto_ativo():
    """
    Retorna o ID do projeto atualmente ativo.
    """

    projeto = obter_projeto_ativo()

    if not projeto:
        return None

    return (
        projeto.get("id")
        or projeto.get("projeto_id")
    )


def listar_conteudos_pendentes_preparacao():
    """
    Lista conteúdos do projeto ativo que
    ainda não possuem metadados completos.
    """

    projeto_id = obter_id_projeto_ativo()

    if not projeto_id:
        return []

    conteudos = listar_conteudos(
        projeto_id=projeto_id
    )

    pendentes = []

    for conteudo in conteudos:
        metadados = obter_metadados(
            conteudo["id"]
        )

        if (
            metadados is None
            or not metadados.get("titulo")
        ):
            pendentes.append(
                conteudo
            )

    return pendentes


def preencher_descricao():
    """
    Permite digitar uma descrição
    com várias linhas.

    Uma linha vazia encerra.
    """

    print(
        "\nDigite a descrição."
    )

    print(
        "Finalize pressionando ENTER "
        "em uma linha vazia."
    )

    linhas = []

    while True:
        linha = input()

        if not linha:
            break

        linhas.append(
            linha
        )

    return "\n".join(
        linhas
    ).strip()


def selecionar_playlist():
    """
    Consulta as playlists do canal
    e permite selecionar uma.
    """

    print(
        "\nConsultando playlists..."
    )

    playlists = (
        listar_playlists_youtube()
    )

    if not playlists:
        print(
            "\nNenhuma playlist disponível."
        )

        return None

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

        indice = int(
            escolha
        ) - 1

        if (
            indice < 0
            or indice >= len(playlists)
        ):
            print(
                "Opção inválida."
            )
            continue

        return playlists[
            indice
        ]


def localizar_thumbnail(
    nome_arquivo,
):
    """
    Procura no Drive a thumbnail
    correspondente ao conteúdo.

    Não baixa a imagem neste momento.

    Apenas registra no banco a referência
    ao arquivo existente no Drive.
    """

    print(
        "\nProcurando thumbnail no Drive..."
    )

    thumbnail = buscar_thumbnail_drive(
        nome_arquivo
    )

    if thumbnail is None:
        print(
            "\nThumbnail não encontrada."
        )

        return (
            None,
            None,
        )

    thumbnail_id = thumbnail.get(
        "id"
    )

    thumbnail_nome = thumbnail.get(
        "name"
    )

    print(
        "\nThumbnail encontrada:"
    )

    print(
        f"Arquivo : {thumbnail_nome}"
    )

    print(
        f"Drive ID: {thumbnail_id}"
    )

    return (
        thumbnail_id,
        thumbnail_nome,
    )


def mostrar_dados_conteudo(
    conteudo,
):
    """
    Mostra informações básicas
    do conteúdo selecionado.
    """

    print(
        "\n========================================"
    )

    print(
        "        PREPARAR CONTEÚDO"
    )

    print(
        "========================================"
    )

    print(
        f"ID global : {conteudo['id']}"
    )

    print(
        f"ID legado : "
        f"{conteudo.get('id_legado') or '-'}"
    )

    print(
        f"Arquivo   : "
        f"{conteudo.get('nome_arquivo') or '-'}"
    )

    print(
        f"Tipo      : "
        f"{conteudo.get('tipo') or '-'}"
    )

    print(
        f"Status    : "
        f"{conteudo.get('status') or '-'}"
    )

    print(
        "========================================"
    )


def preparar_proximo_conteudo():
    """
    Prepara o próximo conteúdo pendente,
    gravando título, descrição, hashtags,
    playlist e thumbnail no SQLite.
    """

    pendentes = (
        listar_conteudos_pendentes_preparacao()
    )

    if not pendentes:
        print(
            "\nNenhum conteúdo aguardando "
            "preparação."
        )

        return

    conteudo = pendentes[0]

    mostrar_dados_conteudo(
        conteudo
    )

    titulo = input(
        "\nTítulo: "
    ).strip()

    if not titulo:
        print(
            "\nO título não pode ficar vazio."
        )

        return

    descricao = preencher_descricao()

    hashtags = input(
        "\nHashtags: "
    ).strip()

    playlist = selecionar_playlist()

    nome_arquivo = conteudo.get(
        "nome_arquivo"
    )

    thumbnail_drive_id = None
    thumbnail_nome_arquivo = None

    if nome_arquivo:
        procurar = input(
            "\nProcurar thumbnail para este "
            "conteúdo? [S/N]: "
        ).strip().lower()

        if procurar == "s":
            (
                thumbnail_drive_id,
                thumbnail_nome_arquivo,
            ) = localizar_thumbnail(
                nome_arquivo
            )

    print(
        "\n========================================"
    )

    print(
        "              RESUMO"
    )

    print(
        "========================================"
    )

    print(
        f"Título    : {titulo}"
    )

    print(
        f"Hashtags  : "
        f"{hashtags or '-'}"
    )

    if playlist:
        print(
            f"Playlist  : "
            f"{playlist['nome']}"
        )
    else:
        print(
            "Playlist  : nenhuma"
        )

    if thumbnail_nome_arquivo:
        print(
            f"Thumbnail : "
            f"{thumbnail_nome_arquivo}"
        )
    else:
        print(
            "Thumbnail : nenhuma"
        )

    print(
        "========================================"
    )

    confirmar = input(
        "\nSalvar estas informações? [S/N]: "
    ).strip().lower()

    if confirmar != "s":
        print(
            "\nOperação cancelada."
        )

        return

    salvar_metadados(
        conteudo_id=conteudo["id"],
        titulo=titulo,
        descricao=descricao,
        hashtags=hashtags,
        playlist_id=(
            playlist["id"]
            if playlist
            else None
        ),
        playlist_nome=(
            playlist["nome"]
            if playlist
            else None
        ),
        thumbnail_drive_id=(
            thumbnail_drive_id
        ),
        thumbnail_nome_arquivo=(
            thumbnail_nome_arquivo
        ),
    )

    print(
        "\n========================================"
    )

    print(
        "CONTEÚDO PREPARADO COM SUCESSO"
    )

    print(
        "========================================"
    )


def listar_pendentes():
    """
    Mostra conteúdos que ainda aguardam
    preparação.
    """

    pendentes = (
        listar_conteudos_pendentes_preparacao()
    )

    print(
        "\n========================================"
    )

    print(
        "     CONTEÚDOS A PREPARAR"
    )

    print(
        "========================================"
    )

    if not pendentes:
        print(
            "\nNenhum conteúdo pendente."
        )

        return

    for indice, conteudo in enumerate(
        pendentes,
        start=1,
    ):
        print(
            f"\n{indice} - "
            f"{conteudo.get('id_legado') or conteudo['id']}"
        )

        print(
            f"    "
            f"{conteudo.get('nome_arquivo') or '-'}"
        )

    print(
        "\n========================================"
    )


def mostrar_resumo():
    """
    Exibe um resumo simples dos conteúdos
    e metadados do projeto ativo.
    """

    projeto_id = obter_id_projeto_ativo()

    if not projeto_id:
        print(
            "\nNenhum projeto ativo."
        )

        return

    conteudos = listar_conteudos(
        projeto_id=projeto_id
    )

    preparados = 0
    com_thumbnail = 0

    for conteudo in conteudos:
        metadados = obter_metadados(
            conteudo["id"]
        )

        if (
            metadados
            and metadados.get("titulo")
        ):
            preparados += 1

        if (
            metadados
            and metadados.get(
                "thumbnail_drive_id"
            )
        ):
            com_thumbnail += 1

    aguardando = len(
        listar_conteudos_pendentes_preparacao()
    )

    print(
        "\n========================================"
    )

    print(
        "        RESUMO DE CONTEÚDOS"
    )

    print(
        "========================================"
    )

    print(
        f"Total              : {len(conteudos)}"
    )

    print(
        f"Preparados         : {preparados}"
    )

    print(
        f"Aguardando preparo : {aguardando}"
    )

    print(
        f"Com thumbnail      : {com_thumbnail}"
    )

    print(
        "========================================"
    )


def mostrar_cabecalho():
    """
    Mostra o cabeçalho do novo
    gerenciador SQLite.
    """

    projeto = obter_projeto_ativo()

    print(
        "\n========================================"
    )

    print(
        "      GERENCIAR CONTEÚDOS"
    )

    print(
        "========================================"
    )

    if projeto:
        print(
            f"Projeto ativo: "
            f"{projeto.get('nome', '-')}"
        )
    else:
        print(
            "Projeto ativo: NENHUM"
        )


def iniciar():
    """
    Menu do gerenciador de conteúdos
    baseado no banco SQLite.
    """

    while True:
        mostrar_cabecalho()

        print(
            "\n1 - Preparar próximo conteúdo"
        )

        print(
            "2 - Ver conteúdos a preparar"
        )

        print(
            "3 - Ver resumo"
        )

        print(
            "0 - Voltar"
        )

        opcao = input(
            "\nEscolha uma opção: "
        ).strip()

        if opcao == "1":
            preparar_proximo_conteudo()

        elif opcao == "2":
            listar_pendentes()

        elif opcao == "3":
            mostrar_resumo()

        elif opcao == "0":
            break

        else:
            print(
                "\nOpção inválida."
            )


if __name__ == "__main__":
    iniciar()