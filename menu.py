# -*- coding: utf-8 -*-

from version import obter_identificacao

from core.logger import obter_logger
from core.diagnostico import executar_diagnostico

from core.projetos import (
    listar_projetos,
    mostrar_projeto_ativo,
    obter_projeto_ativo,
    selecionar_projeto,
)

from core.drive import (
    baixar_thumbnail,
    mostrar_videos_pendentes,
    testar_conexao_drive,
    testar_thumbnail_video,
)

from core.pipeline import excluir_arquivo_temporario

from core.repositorio import (
    listar_conteudos,
    obter_metadados,
)
from core.repositorio_publicacao import listar_publicacoes
from core.servico_publicacao_db import servico_publicacao_db

from core.youtube import (
    definir_thumbnail_youtube,
    listar_canais_youtube,
    listar_playlists_youtube,
)

from core.sincronizacao_db import (
    sincronizar_videos_pendentes_db,
)

from ferramentas.gerenciar_conteudos_db import (
    iniciar as iniciar_gerenciador_conteudos,
)


logger = obter_logger()


NOMES_PRIVACIDADE = {
    "private": "PRIVADO",
    "public": "PÚBLICO",
    "unlisted": "NÃO LISTADO",
}


STATUS_PUBLICACAO_BLOQUEANTES = {
    "AGUARDANDO",
    "PROCESSANDO",
    "PARCIAL",
    "CONCLUIDO",
}


def obter_id_projeto_ativo():
    projeto = obter_projeto_ativo()

    if not projeto:
        return None

    return projeto.get("id") or projeto.get("projeto_id")


def conteudo_tem_publicacao_bloqueante(conteudo_id):
    publicacoes = listar_publicacoes(
        conteudo_id=conteudo_id,
        plataforma="YOUTUBE",
    )

    for publicacao in publicacoes:
        status = str(publicacao.get("status") or "").upper()

        if status in STATUS_PUBLICACAO_BLOQUEANTES:
            return True

    return False


def listar_conteudos_aptos_publicacao():
    projeto_id = obter_id_projeto_ativo()

    if not projeto_id:
        return []

    conteudos = listar_conteudos(
        projeto_id=projeto_id,
        status="PENDENTE",
    )

    aptos = []

    for conteudo in conteudos:
        conteudo_id = conteudo["id"]
        metadados = obter_metadados(conteudo_id)

        if not metadados:
            continue

        if not metadados.get("titulo"):
            continue

        if not conteudo.get("drive_file_id"):
            continue

        if conteudo_tem_publicacao_bloqueante(conteudo_id):
            continue

        aptos.append(
            {
                "conteudo": conteudo,
                "metadados": metadados,
            }
        )

    return aptos


def mostrar_conteudo_resumido(item, indice=None):
    conteudo = item["conteudo"]
    metadados = item["metadados"]

    prefixo = f"{indice} - " if indice is not None else ""
    id_legado = conteudo.get("id_legado") or conteudo.get("id")
    titulo = (
        metadados.get("titulo")
        or conteudo.get("nome_arquivo")
        or "Sem título"
    )
    tipo = conteudo.get("tipo") or "não informado"

    print(
        f"{prefixo}{id_legado} | {tipo} | {titulo}"
    )


def exibir_opcoes():
    identificacao = obter_identificacao()

    print("\n========================================")
    print(f"      {identificacao}")
    print("========================================")

    projeto = obter_projeto_ativo()

    if projeto:
        print(f"Projeto ativo: {projeto['nome']}")
    else:
        print("Projeto ativo: NENHUM")

    print("\nDRIVE")
    print("1 - Testar conexão com Google Drive")
    print("2 - Listar vídeos pendentes")

    print("\nCONTEÚDOS")
    print("3 - Sincronizar Drive → Banco")
    print("4 - Gerenciar conteúdos")

    print("\nYOUTUBE")
    print("5 - Listar canais do YouTube")
    print("6 - Listar playlists do YouTube")

    print("\nPUBLICAÇÃO")
    print("7 - Mostrar próximo conteúdo")
    print("8 - Publicar próximo conteúdo")
    print("9 - Publicar conteúdos em lote")
    print("10 - Escolher conteúdo para publicar")

    print("\nPROJETOS")
    print("11 - Listar projetos")
    print("12 - Trocar projeto")
    print("13 - Mostrar projeto ativo")

    print("\nSISTEMA")
    print("14 - Diagnóstico do ambiente")

    print("\n0 - Sair")

def mostrar_erro_operacao(
    nome_operacao,
):
    print(
        "\n========================================"
    )

    print(
        "       ERRO DURANTE A OPERAÇÃO"
    )

    print(
        "========================================"
    )

    print(
        f"Operação: {nome_operacao}"
    )

    print()

    print(
        "O AutoTube encontrou um erro, "
        "mas continuará funcionando."
    )

    print(
        "Os detalhes técnicos foram "
        "registrados no arquivo de log."
    )

    print(
        "========================================"
    )

    input(
        "\nPressione ENTER para voltar ao menu..."
    )


def executar_operacao(
    nome_operacao,
    funcao,
    *args,
    **kwargs,
):
    try:
        logger.info(
            "Operação iniciada | operacao=%s",
            nome_operacao,
        )

        resultado = funcao(
            *args,
            **kwargs,
        )

        logger.info(
            "Operação finalizada | operacao=%s",
            nome_operacao,
        )

        return resultado

    except Exception:
        logger.exception(
            "Erro durante operação | operacao=%s",
            nome_operacao,
        )

        mostrar_erro_operacao(
            nome_operacao
        )

        return None


def selecionar_privacidade():
    while True:
        print(
            "\n===== VISIBILIDADE ====="
        )

        print(
            "1 - Privado"
        )

        print(
            "2 - Público"
        )

        print(
            "3 - Não listado"
        )

        print(
            "0 - Cancelar"
        )

        print(
            "========================"
        )

        opcao = input(
            "\nEscolha uma opção: "
        ).strip()

        if opcao == "1":
            return "private"

        if opcao == "2":
            return "public"

        if opcao == "3":
            return "unlisted"

        if opcao == "0":
            print(
                "\nOperação cancelada."
            )

            logger.info(
                "Seleção de privacidade cancelada"
            )

            return None

        print(
            "\nOpção inválida. "
            "Escolha 1, 2, 3 ou 0."
        )


def selecionar_quantidade_lote():
    while True:
        print(
            "\n===== TAMANHO DO LOTE ====="
        )

        print(
            "1 - Publicar 2 vídeos"
        )

        print(
            "2 - Publicar 3 vídeos"
        )

        print(
            "0 - Cancelar"
        )

        print(
            "==========================="
        )

        opcao = input(
            "\nEscolha uma opção: "
        ).strip()

        if opcao == "1":
            return 2

        if opcao == "2":
            return 3

        if opcao == "0":
            print(
                "\nPublicação em lote cancelada."
            )

            logger.info(
                "Publicação em lote cancelada"
            )

            return None

        print(
            "\nOpção inválida. "
            "Escolha 1, 2 ou 0."
        )


def mostrar_proximo_conteudo_db():
    aptos = listar_conteudos_aptos_publicacao()

    if not aptos:
        print("\nNenhum conteúdo apto para publicação.")
        return

    print("\n===== PRÓXIMO CONTEÚDO =====")
    mostrar_conteudo_resumido(aptos[0])
    print("============================")


def confirmar_publicacao_item(item, privacidade):
    nome_privacidade = NOMES_PRIVACIDADE.get(
        privacidade,
        privacidade.upper(),
    )

    print("\n===== CONFIRMAÇÃO =====")
    mostrar_conteudo_resumido(item)
    print(f"Visibilidade: {nome_privacidade}")
    print("=======================")

    confirmar = input(
        "\nConfirmar publicação? [S/N]: "
    ).strip().lower()

    return confirmar == "s"


def criar_e_executar_publicacao(item, privacidade):
    conteudo = item["conteudo"]

    solicitacao = servico_publicacao_db.criar_solicitacao(
        conteudo_id=conteudo["id"],
        privacidade=privacidade,
    )

    publicacao_id = solicitacao["publicacao_id"]

    print("\nSolicitação criada:")
    print(publicacao_id)

    return servico_publicacao_db.executar_publicacao(
        publicacao_id
    )


def publicar_proximo_conteudo_cli():
    aptos = listar_conteudos_aptos_publicacao()

    if not aptos:
        print("\nNenhum conteúdo apto para publicação.")
        return

    item = aptos[0]

    print("\nPróximo conteúdo:")
    mostrar_conteudo_resumido(item)

    privacidade = selecionar_privacidade()

    if privacidade is None:
        return

    if not confirmar_publicacao_item(item, privacidade):
        print("\nPublicação cancelada.")
        return

    criar_e_executar_publicacao(item, privacidade)


def selecionar_conteudo_publicacao():
    aptos = listar_conteudos_aptos_publicacao()

    if not aptos:
        print("\nNenhum conteúdo apto para publicação.")
        return None

    print("\n===== CONTEÚDOS APTOS =====")

    for indice, item in enumerate(aptos, start=1):
        mostrar_conteudo_resumido(
            item,
            indice=indice,
        )

    print("0 - Cancelar")
    print("===========================")

    while True:
        escolha = input(
            "\nEscolha o conteúdo: "
        ).strip()

        if escolha == "0":
            print("\nOperação cancelada.")
            return None

        try:
            indice = int(escolha)
        except ValueError:
            print("\nOpção inválida.")
            continue

        if 1 <= indice <= len(aptos):
            return aptos[indice - 1]

        print("\nOpção inválida.")


def publicar_conteudo_escolhido_cli():
    item = selecionar_conteudo_publicacao()

    if item is None:
        return

    privacidade = selecionar_privacidade()

    if privacidade is None:
        return

    if not confirmar_publicacao_item(item, privacidade):
        print("\nPublicação cancelada.")
        return

    criar_e_executar_publicacao(item, privacidade)


def publicar_conteudos_em_lote_cli():
    quantidade = selecionar_quantidade_lote()

    if quantidade is None:
        return

    aptos = listar_conteudos_aptos_publicacao()

    if not aptos:
        print("\nNenhum conteúdo apto para publicação.")
        return

    selecionados = aptos[:quantidade]

    if len(selecionados) < quantidade:
        print(
            "\nAtenção: existem apenas "
            f"{len(selecionados)} conteúdos aptos."
        )

    privacidade = selecionar_privacidade()

    if privacidade is None:
        return

    nome_privacidade = NOMES_PRIVACIDADE.get(
        privacidade,
        privacidade.upper(),
    )

    print("\n===== CONFIRMAÇÃO DO LOTE =====")

    for indice, item in enumerate(
        selecionados,
        start=1,
    ):
        mostrar_conteudo_resumido(
            item,
            indice=indice,
        )

    print(
        f"Quantidade   : {len(selecionados)} vídeos"
    )
    print(f"Visibilidade : {nome_privacidade}")
    print("===============================")

    confirmar = input(
        f"\nPublicar {len(selecionados)} vídeos como "
        f"{nome_privacidade}? [S/N]: "
    ).strip().lower()

    if confirmar != "s":
        print("\nPublicação em lote cancelada.")
        logger.info(
            "Publicação em lote cancelada pelo usuário | "
            "quantidade=%s | privacidade=%s",
            len(selecionados),
            privacidade,
        )
        return

    for indice, item in enumerate(
        selecionados,
        start=1,
    ):
        print("\n========================================")
        print(
            f"PUBLICAÇÃO {indice}/"
            f"{len(selecionados)}"
        )
        print("========================================")
        mostrar_conteudo_resumido(item)

        resultado = criar_e_executar_publicacao(
            item,
            privacidade,
        )

        if resultado is None:
            print(
                "\nLote interrompido: "
                "publicação sem resultado."
            )
            break

        if not resultado.sucesso:
            print("\nLote interrompido após falha.")
            break

# =========================================================
# FUNÇÕES LEGADAS DE TESTE DE THUMBNAIL
# Mantidas temporariamente fora do menu principal.
# =========================================================

def testar_localizacao_thumbnail():
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
            executar_operacao(
                "Testar conexão com Google Drive",
                testar_conexao_drive,
            )

        elif opcao == "2":
            executar_operacao(
                "Listar vídeos pendentes",
                mostrar_videos_pendentes,
            )

        elif opcao == "3":
            executar_operacao(
                "Sincronizar Drive com banco",
                sincronizar_videos_pendentes_db,
            )

        elif opcao == "4":
            executar_operacao(
                "Gerenciar conteúdos",
                iniciar_gerenciador_conteudos,
            )

        elif opcao == "5":
            executar_operacao(
                "Listar canais do YouTube",
                listar_canais_youtube,
            )

        elif opcao == "6":
            executar_operacao(
                "Listar playlists do YouTube",
                listar_playlists_youtube,
            )

        elif opcao == "7":
            executar_operacao(
                "Mostrar próximo conteúdo",
                mostrar_proximo_conteudo_db,
            )

        elif opcao == "8":
            executar_operacao(
                "Publicar próximo conteúdo",
                publicar_proximo_conteudo_cli,
            )

        elif opcao == "9":
            executar_operacao(
                "Publicar conteúdos em lote",
                publicar_conteudos_em_lote_cli,
            )

        elif opcao == "10":
            executar_operacao(
                "Escolher conteúdo para publicar",
                publicar_conteudo_escolhido_cli,
            )

        elif opcao == "11":
            executar_operacao(
                "Listar projetos",
                listar_projetos,
            )

        elif opcao == "12":
            executar_operacao(
                "Trocar projeto",
                selecionar_projeto,
            )

        elif opcao == "13":
            executar_operacao(
                "Mostrar projeto ativo",
                mostrar_projeto_ativo,
            )

        elif opcao == "14":
            executar_operacao(
                "Diagnóstico do ambiente",
                executar_diagnostico,
            )

        elif opcao == "0":
            print("\nSaindo do AutoTube...")
            logger.info(
                "Saída solicitada pelo usuário"
            )
            break

        else:
            print("\nOpção inválida.")