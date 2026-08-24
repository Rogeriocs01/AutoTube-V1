from core.projetos import (
    listar_projetos,
    mostrar_projeto_ativo,
    obter_projeto_ativo,
    selecionar_projeto,
)

from core.controle import (
    criar_controle_videos,
    mostrar_proximo_video,
    mostrar_resumo_controle,
)

from core.drive import (
    baixar_thumbnail,
    mostrar_videos_pendentes,
    testar_conexao_drive,
    testar_thumbnail_video,
)

from core.pipeline import (
    excluir_arquivo_temporario,
    publicar_proximo_video,
    publicar_video_escolhido,
    publicar_videos_em_lote,
)

from core.youtube import (
    definir_thumbnail_youtube,
    listar_canais_youtube,
    listar_playlists_youtube,
)


def exibir_opcoes():
    print("\n==========================")
    print("       AUTOTUBE V1")
    print("==========================")

    projeto = obter_projeto_ativo()

    if projeto:
        print(
            f"Projeto ativo: "
            f"{projeto['nome']}"
        )
    else:
        print("Projeto ativo: NENHUM")

    print("\nDRIVE")
    print("1 - Testar conexão com Google Drive")
    print("2 - Listar vídeos pendentes")
    print("14 - Testar localização de thumbnail")

    print("\nCONTROLE")
    print("3 - Sincronizar vídeos pendentes")
    print("4 - Ver resumo do controle")

    print("\nYOUTUBE")
    print("5 - Listar canais do YouTube")
    print("6 - Mostrar próximo vídeo")
    print("12 - Listar playlists do YouTube")
    print("15 - Testar aplicação de thumbnail")

    print("\nPUBLICAÇÃO")
    print("7 - Publicar próximo vídeo")
    print("8 - Publicar vídeos em lote")
    print("13 - Escolher vídeo para publicar")

    print("\nPROJETOS")
    print("9 - Listar projetos")
    print("10 - Trocar projeto")
    print("11 - Mostrar projeto ativo")

    print("\n0 - Sair")


def testar_aplicacao_thumbnail():
    print(
        "\n========================================"
    )
    print(
        "      TESTE DE THUMBNAIL NO YOUTUBE"
    )
    print(
        "========================================"
    )

    nome_video = input(
        "\nNome completo do vídeo: "
    ).strip()

    if not nome_video:
        print(
            "\nNome do vídeo não informado."
        )
        return

    youtube_id = input(
        "YouTube ID do vídeo já publicado: "
    ).strip()

    if not youtube_id:
        print(
            "\nYouTube ID não informado."
        )
        return

    print(
        "\nProcurando e baixando thumbnail..."
    )

    caminho_thumbnail = baixar_thumbnail(
        nome_video=nome_video
    )

    if caminho_thumbnail is None:
        print(
            "\nNão foi possível localizar "
            "ou baixar a thumbnail."
        )
        return

    print(
        "\nThumbnail preparada:"
    )
    print(
        caminho_thumbnail
    )

    confirmar = input(
        "\nAplicar esta thumbnail "
        "ao vídeo do YouTube? [S/N]: "
    ).strip().lower()

    if confirmar != "s":
        print(
            "\nTeste cancelado."
        )

        excluir_arquivo_temporario(
            caminho_thumbnail
        )

        return

    sucesso = definir_thumbnail_youtube(
        youtube_id=youtube_id,
        caminho_thumbnail=caminho_thumbnail,
    )

    excluir_arquivo_temporario(
        caminho_thumbnail
    )

    if sucesso:
        print(
            "\n========================================"
        )
        print(
            "THUMBNAIL APLICADA COM SUCESSO"
        )
        print(
            "========================================"
        )

    else:
        print(
            "\n========================================"
        )
        print(
            "FALHA AO APLICAR THUMBNAIL"
        )
        print(
            "========================================"
        )


def iniciar():
    while True:
        exibir_opcoes()

        opcao = input(
            "\nEscolha uma opção: "
        ).strip()

        if opcao == "1":
            testar_conexao_drive()

        elif opcao == "2":
            mostrar_videos_pendentes()

        elif opcao == "3":
            criar_controle_videos()

        elif opcao == "4":
            mostrar_resumo_controle()

        elif opcao == "5":
            listar_canais_youtube()

        elif opcao == "6":
            mostrar_proximo_video()

        elif opcao == "7":
            publicar_proximo_video()

        elif opcao == "8":
            publicar_videos_em_lote()

        elif opcao == "9":
            listar_projetos()

        elif opcao == "10":
            selecionar_projeto()

        elif opcao == "11":
            mostrar_projeto_ativo()

        elif opcao == "12":
            listar_playlists_youtube()

        elif opcao == "13":
            publicar_video_escolhido()

        elif opcao == "14":
            nome_video = input(
                "\nDigite o nome completo do vídeo: "
            ).strip()

            if nome_video:
                testar_thumbnail_video(
                    nome_video
                )
            else:
                print(
                    "\nNome do vídeo não informado."
                )

        elif opcao == "15":
            testar_aplicacao_thumbnail()

        elif opcao == "0":
            print(
                "\nSaindo do AutoTube..."
            )
            break

        else:
            print(
                "\nOpção inválida."
            )