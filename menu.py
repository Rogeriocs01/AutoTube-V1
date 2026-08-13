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
    mostrar_videos_pendentes,
    testar_conexao_drive,
)

from core.pipeline import (
    publicar_proximo_video,
    publicar_videos_em_lote,
)

from core.youtube import listar_canais_youtube


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

    print("\nCONTROLE")
    print("3 - Criar controle videos.json")
    print("4 - Ver resumo do controle")

    print("\nYOUTUBE")
    print("5 - Listar canais do YouTube")
    print("6 - Mostrar próximo vídeo")

    print("\nPUBLICAÇÃO")
    print("7 - Publicar próximo vídeo")
    print("8 - Publicar vídeos em lote")

    print("\nPROJETOS")
    print("9 - Listar projetos")
    print("10 - Trocar projeto")
    print("11 - Mostrar projeto ativo")

    print("\n0 - Sair")


def iniciar():
    while True:
        exibir_opcoes()

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            testar_conexao_drive()

        elif opcao == "2":
            mostrar_videos_pendentes()

        elif opcao == "3":
            confirmar = input(
                "\nIsso substituirá o videos.json atual. "
                "Continuar? [S/N]: "
            ).strip().lower()

            if confirmar == "s":
                criar_controle_videos()
            else:
                print("\nOperação cancelada.")

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

        elif opcao == "0":
            print("\nSaindo do AutoTube...")
            break

        else:
            print("\nOpção inválida.")