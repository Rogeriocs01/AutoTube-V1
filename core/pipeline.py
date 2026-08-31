from core.controle import (
    obter_proximo_video_pendente,
    registrar_video_publicado,
    selecionar_video_pendente,
)

from core.drive import (
    baixar_thumbnail,
    baixar_video,
    mover_video_para_publicados,
)

from core.metadados import buscar_metadados

from core.youtube import (
    adicionar_video_playlist,
    definir_thumbnail_youtube,
    obter_canal_youtube_autenticado,
    publicar_video,
    validar_canal_youtube,
)

from core.projetos import obter_projeto_ativo
from core.logger import obter_logger


logger = obter_logger()


NOMES_PRIVACIDADE = {
    "private": "PRIVADO",
    "public": "PÚBLICO",
    "unlisted": "NÃO LISTADO",
}


def selecionar_privacidade():
    while True:
        print("\n===== VISIBILIDADE =====")
        print("1 - Privado")
        print("2 - Público")
        print("3 - Não listado")
        print("0 - Cancelar")
        print("========================")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            return "private"

        if opcao == "2":
            return "public"

        if opcao == "3":
            return "unlisted"

        if opcao == "0":
            print("\nOperação cancelada.")
            logger.info("Seleção de privacidade cancelada")
            return None

        print("\nOpção inválida. Escolha 1, 2, 3 ou 0.")


def selecionar_quantidade_lote():
    while True:
        print("\n===== TAMANHO DO LOTE =====")
        print("1 - Publicar 2 vídeos")
        print("2 - Publicar 3 vídeos")
        print("0 - Cancelar")
        print("===========================")

        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            return 2

        if opcao == "2":
            return 3

        if opcao == "0":
            print("\nPublicação em lote cancelada.")
            logger.info("Publicação em lote cancelada")
            return None

        print("\nOpção inválida. Escolha 1, 2 ou 0.")


def excluir_arquivo_temporario(caminho_local):
    if caminho_local is None:
        return

    if not caminho_local.exists():
        return

    try:
        caminho_local.unlink()
        print("Arquivo temporário excluído.")

    except OSError as erro:
        print(
            "Não foi possível excluir o arquivo temporário: "
            f"{erro}"
        )

        logger.warning(
            "Falha ao excluir arquivo temporário | "
            "arquivo=%s | erro=%s",
            caminho_local,
            erro,
        )


def preparar_proximo_video(video_id, video):
    print("\n===== PREPARANDO PRÓXIMO VÍDEO =====")
    print(f"ID interno : {video_id}")
    print(f"Arquivo    : {video.get('arquivo')}")
    print("====================================")

    caminho_local = baixar_video(
        drive_id=video["drive_id"],
        nome_arquivo=video["arquivo"],
    )

    if caminho_local is None:
        print("\nNão foi possível preparar o vídeo.")

        logger.error(
            "Falha ao baixar vídeo | "
            "video_id=%s | arquivo=%s",
            video_id,
            video.get("arquivo"),
        )

        return None

    print("\nVídeo preparado com sucesso.")
    print(f"Local: {caminho_local}")

    logger.info(
        "Vídeo preparado | "
        "video_id=%s | arquivo=%s",
        video_id,
        video.get("arquivo"),
    )

    return caminho_local


def processar_publicacao(
    video_id,
    video,
    privacidade,
    pedir_confirmacao=True,
):
    nome_arquivo = str(
        video.get("arquivo", "")
    ).strip()

    if not nome_arquivo:
        print(
            "\nO vídeo pendente não possui "
            "nome de arquivo."
        )
        print(f"ID interno: {video_id}")

        logger.error(
            "Vídeo pendente sem nome de arquivo | "
            "video_id=%s",
            video_id,
        )

        return False

    logger.info(
        "Publicação iniciada | "
        "video_id=%s | arquivo=%s | privacidade=%s",
        video_id,
        nome_arquivo,
        privacidade,
    )

    projeto = obter_projeto_ativo()

    if projeto is None:
        print("\nNenhum projeto ativo.")

        logger.error(
            "Publicação interrompida | "
            "motivo=nenhum projeto ativo | "
            "video_id=%s",
            video_id,
        )

        return False

    logger.info(
        "Projeto identificado | projeto=%s",
        projeto["nome"],
    )

    metadados = buscar_metadados(
        nome_arquivo
    )

    if metadados is None:
        print(
            "\nO vídeo permanece pendente."
        )

        logger.warning(
            "Publicação interrompida | "
            "motivo=metadados não encontrados | "
            "video_id=%s | arquivo=%s",
            video_id,
            nome_arquivo,
        )

        return False

    if not validar_canal_youtube():
        print(
            "\nPublicação cancelada "
            "por segurança."
        )

        logger.warning(
            "Publicação interrompida | "
            "motivo=validação do canal falhou | "
            "video_id=%s",
            video_id,
        )

        return False

    canal = obter_canal_youtube_autenticado()

    if canal is None:
        print(
            "\nNão foi possível identificar "
            "o canal autenticado."
        )

        logger.error(
            "Publicação interrompida | "
            "motivo=canal autenticado não identificado | "
            "video_id=%s",
            video_id,
        )

        return False

    logger.info(
        "Canal confirmado | "
        "canal=%s | canal_id=%s",
        canal["nome"],
        canal["id"],
    )

    playlist_id = metadados.get(
        "playlist_id",
        "",
    )

    playlist_nome = metadados.get(
        "playlist_nome",
        "",
    )

    if playlist_nome:
        nome_playlist = playlist_nome
    else:
        nome_playlist = "Nenhuma"

    print(
        "\nProcurando thumbnail..."
    )

    caminho_thumbnail = baixar_thumbnail(
        nome_video=nome_arquivo
    )

    if caminho_thumbnail:
        status_thumbnail = (
            f"ENCONTRADA - "
            f"{caminho_thumbnail.name}"
        )

        logger.info(
            "Thumbnail encontrada | "
            "video_id=%s | arquivo=%s",
            video_id,
            caminho_thumbnail.name,
        )

    else:
        status_thumbnail = (
            "NÃO ENCONTRADA"
        )

        logger.info(
            "Thumbnail não encontrada | "
            "video_id=%s",
            video_id,
        )

    caminho_local = preparar_proximo_video(
        video_id=video_id,
        video=video,
    )

    if caminho_local is None:
        if caminho_thumbnail:
            excluir_arquivo_temporario(
                caminho_thumbnail
            )

        return False

    nome_privacidade = (
        NOMES_PRIVACIDADE.get(
            privacidade,
            privacidade.upper(),
        )
    )

    print(
        "\n========================================"
    )
    print(
        "        CONFIRMAÇÃO DE PUBLICAÇÃO"
    )
    print(
        "========================================"
    )

    print(
        f"Projeto      : {projeto['nome']}"
    )

    print(
        f"Canal        : {canal['nome']}"
    )

    print(
        f"Canal ID     : {canal['id']}"
    )

    print(
        f"ID interno   : {video_id}"
    )

    print(
        f"Arquivo      : {caminho_local.name}"
    )

    print(
        f"Título       : {metadados['titulo']}"
    )

    print(
        f"Playlist     : {nome_playlist}"
    )

    print(
        f"Thumbnail    : {status_thumbnail}"
    )

    print(
        f"Visibilidade : {nome_privacidade}"
    )

    print(
        "========================================"
    )

    if pedir_confirmacao:
        confirmar = input(
            "\nCONFIRMAR PUBLICAÇÃO? [S/N]: "
        ).strip().lower()

        if confirmar != "s":
            print(
                "\nPublicação cancelada."
            )

            logger.info(
                "Publicação cancelada pelo usuário | "
                "video_id=%s",
                video_id,
            )

            excluir_arquivo_temporario(
                caminho_local
            )

            if caminho_thumbnail:
                excluir_arquivo_temporario(
                    caminho_thumbnail
                )

            return False

    logger.info(
        "Iniciando upload para YouTube | "
        "video_id=%s",
        video_id,
    )

    youtube_id = publicar_video(
        caminho_video=caminho_local,
        titulo=metadados["titulo"],
        descricao=metadados["descricao"],
        privacidade=privacidade,
    )

    if youtube_id is None:
        print(
            "\nO upload não foi concluído."
        )

        logger.error(
            "Falha no upload para YouTube | "
            "video_id=%s | arquivo=%s",
            video_id,
            nome_arquivo,
        )

        return False

    logger.info(
        "Upload concluído | "
        "video_id=%s | youtube_id=%s",
        video_id,
        youtube_id,
    )

    registrado = registrar_video_publicado(
        video_id=video_id,
        youtube_id=youtube_id,
    )

    if not registrado:
        print(
            "\nATENÇÃO: o vídeo foi enviado "
            "ao YouTube, mas houve erro "
            "ao atualizar videos.json."
        )

        logger.error(
            "Upload realizado mas controle não atualizado | "
            "video_id=%s | youtube_id=%s",
            video_id,
            youtube_id,
        )

        return False

    logger.info(
        "Controle atualizado | "
        "video_id=%s | youtube_id=%s",
        video_id,
        youtube_id,
    )

    playlist_ok = adicionar_video_playlist(
        youtube_id=youtube_id,
        playlist_id=playlist_id,
    )

    if playlist_id:
        if playlist_ok:
            logger.info(
                "Playlist aplicada | "
                "video_id=%s | playlist=%s",
                video_id,
                nome_playlist,
            )
        else:
            logger.warning(
                "Falha ao aplicar playlist | "
                "video_id=%s | playlist=%s",
                video_id,
                nome_playlist,
            )

    if caminho_thumbnail:
        thumbnail_ok = (
            definir_thumbnail_youtube(
                youtube_id=youtube_id,
                caminho_thumbnail=caminho_thumbnail,
            )
        )
    else:
        thumbnail_ok = True

    if caminho_thumbnail:
        if thumbnail_ok:
            logger.info(
                "Thumbnail aplicada | "
                "video_id=%s",
                video_id,
            )
        else:
            logger.warning(
                "Falha ao aplicar thumbnail | "
                "video_id=%s | youtube_id=%s",
                video_id,
                youtube_id,
            )

    movido = mover_video_para_publicados(
        drive_id=video["drive_id"]
    )

    if movido:
        logger.info(
            "Vídeo movido no Drive | "
            "video_id=%s | destino=Publicados",
            video_id,
        )
    else:
        logger.warning(
            "Falha na movimentação do Drive | "
            "video_id=%s",
            video_id,
        )

    if not movido:
        print(
            "\nO vídeo foi publicado, "
            "mas não foi movido para "
            "a pasta Publicados."
        )

    excluir_arquivo_temporario(
        caminho_local
    )

    if caminho_thumbnail:
        excluir_arquivo_temporario(
            caminho_thumbnail
        )

    print(
        "\n========================================"
    )
    print(
        "          PROCESSO CONCLUÍDO"
    )
    print(
        "========================================"
    )

    print(
        f"Projeto      : {projeto['nome']}"
    )

    print(
        f"Canal        : {canal['nome']}"
    )

    print(
        f"ID interno   : {video_id}"
    )

    print(
        f"YouTube ID   : {youtube_id}"
    )

    print(
        f"Título       : {metadados['titulo']}"
    )

    print(
        f"Visibilidade : {nome_privacidade}"
    )

    print(
        "Status       : PUBLICADO"
    )

    if playlist_id:
        if playlist_ok:
            print(
                f"Playlist     : "
                f"{nome_playlist} - OK"
            )
        else:
            print(
                f"Playlist     : "
                f"{nome_playlist} - FALHOU"
            )
    else:
        print(
            "Playlist     : não utilizada"
        )

    if caminho_thumbnail:
        if thumbnail_ok:
            print(
                "Thumbnail    : OK"
            )
        else:
            print(
                "Thumbnail    : FALHOU"
            )
    else:
        print(
            "Thumbnail    : não utilizada"
        )

    if movido:
        print(
            "Drive        : Publicados - OK"
        )
    else:
        print(
            "Drive        : movimentação FALHOU"
        )

    print(
        "Temp         : limpa"
    )

    print(
        "========================================"
    )

    logger.info(
        "Publicação concluída | "
        "video_id=%s | youtube_id=%s | "
        "playlist_ok=%s | thumbnail_ok=%s | drive_ok=%s",
        video_id,
        youtube_id,
        playlist_ok,
        thumbnail_ok,
        movido,
    )

    return True


def publicar_proximo_video():
    video_id, video = obter_proximo_video_pendente()

    if video is None:
        print(
            "\nNenhum vídeo pendente encontrado."
        )

        logger.info(
            "Nenhum vídeo pendente encontrado"
        )

        return

    privacidade = selecionar_privacidade()

    if privacidade is None:
        return

    processar_publicacao(
        video_id=video_id,
        video=video,
        privacidade=privacidade,
        pedir_confirmacao=True,
    )


def publicar_video_escolhido():
    video_id, video = (
        selecionar_video_pendente()
    )

    if video is None:
        return

    privacidade = selecionar_privacidade()

    if privacidade is None:
        return

    processar_publicacao(
        video_id=video_id,
        video=video,
        privacidade=privacidade,
        pedir_confirmacao=True,
    )


def publicar_videos_em_lote():
    quantidade = selecionar_quantidade_lote()

    if quantidade is None:
        return

    privacidade = selecionar_privacidade()

    if privacidade is None:
        return

    nome_privacidade = NOMES_PRIVACIDADE.get(
        privacidade,
        privacidade.upper(),
    )

    print("\n===== CONFIRMAÇÃO DO LOTE =====")
    print(f"Quantidade   : {quantidade} vídeos")
    print(f"Visibilidade : {nome_privacidade}")
    print("===============================")

    confirmar = input(
        f"\nPublicar {quantidade} vídeos como "
        f"{nome_privacidade}? [S/N]: "
    ).strip().lower()

    if confirmar != "s":
        print(
            "\nPublicação em lote cancelada."
        )

        logger.info(
            "Publicação em lote cancelada pelo usuário | "
            "quantidade=%s | privacidade=%s",
            quantidade,
            privacidade,
        )

        return

    publicados = 0
    motivo_interrupcao = None

    logger.info(
        "Publicação em lote iniciada | "
        "quantidade=%s | privacidade=%s",
        quantidade,
        privacidade,
    )

    print(
        "\n===== INICIANDO PUBLICAÇÃO EM LOTE ====="
    )

    for numero_atual in range(
        1,
        quantidade + 1,
    ):
        print(
            f"\n===== VÍDEO {numero_atual} "
            f"DE {quantidade} ====="
        )

        video_id, video = (
            obter_proximo_video_pendente()
        )

        if video is None:
            motivo_interrupcao = (
                "Não existem mais vídeos pendentes."
            )

            logger.warning(
                "Lote interrompido | "
                "motivo=sem vídeos pendentes"
            )

            break

        sucesso = processar_publicacao(
            video_id=video_id,
            video=video,
            privacidade=privacidade,
            pedir_confirmacao=False,
        )

        if not sucesso:
            motivo_interrupcao = (
                "O próximo vídeo não pôde ser publicado. "
                "Verifique as mensagens apresentadas acima."
            )

            logger.warning(
                "Lote interrompido | "
                "video_id=%s | "
                "publicados=%s | solicitados=%s",
                video_id,
                publicados,
                quantidade,
            )

            break

        publicados += 1

    print(
        "\n===== RESUMO DO LOTE ====="
    )

    print(
        f"Solicitados : {quantidade}"
    )

    print(
        f"Publicados  : {publicados}"
    )

    if motivo_interrupcao is None:
        print(
            "Resultado   : lote concluído com sucesso"
        )

        logger.info(
            "Lote concluído | "
            "solicitados=%s | publicados=%s",
            quantidade,
            publicados,
        )

    else:
        print(
            "Resultado   : lote interrompido"
        )
        print(
            f"Motivo      : {motivo_interrupcao}"
        )

    print(
        "=========================="
    )