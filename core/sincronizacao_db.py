from core.controle import selecionar_tipo_conteudo
from core.drive import listar_videos_pendentes
from core.projetos import obter_projeto_ativo
from core.repositorio import (
    listar_conteudos,
    salvar_conteudo,
)


def obter_id_projeto_ativo():
    """
    Retorna o ID do projeto ativo.
    """

    projeto = obter_projeto_ativo()

    if not projeto:
        return None

    return (
        projeto.get("id")
        or projeto.get("projeto_id")
    )


def obter_maior_numero_legado(
    conteudos,
):
    """
    Localiza o maior número entre IDs
    legados no formato YT_0001.
    """

    maior_numero = 0

    for conteudo in conteudos:
        id_legado = conteudo.get(
            "id_legado"
        )

        if not id_legado:
            continue

        if not id_legado.startswith(
            "YT_"
        ):
            continue

        numero = id_legado.replace(
            "YT_",
            "",
            1,
        )

        if not numero.isdigit():
            continue

        numero = int(
            numero
        )

        if numero > maior_numero:
            maior_numero = numero

    return maior_numero


def criar_id_global(
    projeto_id,
    id_legado,
):
    """
    Cria o ID global utilizado
    pelo novo banco.

    Exemplo:
    projeto_002:YT_0016
    """

    return (
        f"{projeto_id}:{id_legado}"
    )


def sincronizar_videos_pendentes_db():
    """
    Sincroniza os vídeos da pasta Pendentes
    do projeto ativo diretamente com SQLite.

    Não altera o videos.json.

    Somente arquivos novos são adicionados.
    """

    projeto = obter_projeto_ativo()

    if not projeto:
        print(
            "\nNenhum projeto ativo."
        )
        return

    projeto_id = obter_id_projeto_ativo()

    if not projeto_id:
        print(
            "\nNão foi possível identificar "
            "o ID do projeto ativo."
        )
        return

    print(
        "\n========================================"
    )
    print(
        "     SINCRONIZAÇÃO DRIVE -> SQLITE"
    )
    print(
        "========================================"
    )
    print(
        f"Projeto: {projeto.get('nome', projeto_id)}"
    )

    videos_drive = listar_videos_pendentes()

    if not videos_drive:
        print(
            "\nNenhum vídeo encontrado "
            "na pasta Pendentes."
        )
        return

    conteudos_existentes = listar_conteudos(
        projeto_id=projeto_id
    )

    drive_ids_existentes = {
        conteudo.get(
            "drive_file_id"
        )
        for conteudo
        in conteudos_existentes
        if conteudo.get(
            "drive_file_id"
        )
    }

    videos_novos = [
        video
        for video in videos_drive
        if video.get("id")
        not in drive_ids_existentes
    ]

    if not videos_novos:
        print(
            "\nNenhum vídeo novo encontrado."
        )
        return

    print(
        "\n===== NOVOS VÍDEOS ENCONTRADOS ====="
    )
    print(
        f"Quantidade: {len(videos_novos)}"
    )
    print(
        "====================================="
    )

    maior_numero = (
        obter_maior_numero_legado(
            conteudos_existentes
        )
    )

    proximo_numero = (
        maior_numero + 1
    )

    novos_registros = []

    for video in videos_novos:
        nome_arquivo = video.get(
            "name"
        )

        drive_file_id = video.get(
            "id"
        )

        if (
            not nome_arquivo
            or not drive_file_id
        ):
            print(
                "\nArquivo ignorado por "
                "dados incompletos."
            )
            continue

        tipo_conteudo = (
            selecionar_tipo_conteudo(
                nome_arquivo
            )
        )

        if tipo_conteudo is None:
            print(
                "\nSincronização cancelada."
            )
            print(
                "Nenhum novo conteúdo "
                "foi registrado."
            )
            return

        id_legado = (
            f"YT_{proximo_numero:04d}"
        )

        conteudo_id = criar_id_global(
            projeto_id,
            id_legado,
        )

        salvar_conteudo(
            conteudo_id=conteudo_id,
            projeto_id=projeto_id,
            id_legado=id_legado,
            tipo=tipo_conteudo,
            nome_arquivo=nome_arquivo,
            origem="GOOGLE_DRIVE",
            drive_file_id=drive_file_id,
            status="PENDENTE",
        )

        novos_registros.append(
            conteudo_id
        )

        nome_tipo = (
            "SHORT"
            if tipo_conteudo == "short"
            else "LONGO"
        )

        print(
            "\nRegistrado:"
        )
        print(
            f"ID global : {conteudo_id}"
        )
        print(
            f"ID legado : {id_legado}"
        )
        print(
            f"Arquivo   : {nome_arquivo}"
        )
        print(
            f"Tipo      : {nome_tipo}"
        )

        proximo_numero += 1

    print(
        "\n========================================"
    )
    print(
        "      SINCRONIZAÇÃO CONCLUÍDA"
    )
    print(
        "========================================"
    )
    print(
        f"Novos conteúdos: "
        f"{len(novos_registros)}"
    )
    print(
        f"Total no banco  : "
        f"{len(conteudos_existentes) + len(novos_registros)}"
    )
    print(
        "========================================"
    )


if __name__ == "__main__":
    sincronizar_videos_pendentes_db()