from core.drive import (
    baixar_thumbnail,
    baixar_video,
    mover_video_para_publicados,
)

from core.youtube import (
    adicionar_video_playlist,
    definir_thumbnail_youtube,
    obter_canal_youtube_autenticado,
    publicar_video,
    validar_canal_youtube,
)

from core.projetos import obter_projeto_ativo
from core.logger import obter_logger

from core.resultado_publicacao import (
    ResultadoPublicacao,
)


logger = obter_logger()


NOMES_PRIVACIDADE = {
    "private": "PRIVADO",
    "public": "PÚBLICO",
    "unlisted": "NÃO LISTADO",
}


def excluir_arquivo_temporario(
    caminho_local,
):
    if caminho_local is None:
        return

    if not caminho_local.exists():
        return

    try:
        caminho_local.unlink()

        print(
            "Arquivo temporário excluído."
        )

    except OSError as erro:
        print(
            "Não foi possível excluir "
            "o arquivo temporário: "
            f"{erro}"
        )

        logger.warning(
            "Falha ao excluir arquivo temporário | "
            "arquivo=%s | erro=%s",
            caminho_local,
            erro,
        )


def preparar_proximo_video(
    video_id,
    video,
):
    print(
        "\n===== PREPARANDO PRÓXIMO VÍDEO ====="
    )

    print(
        f"ID interno : {video_id}"
    )

    print(
        f"Arquivo    : {video.get('arquivo')}"
    )

    print(
        "===================================="
    )

    caminho_local = baixar_video(
        drive_id=video["drive_id"],
        nome_arquivo=video["arquivo"],
    )

    if caminho_local is None:
        print(
            "\nNão foi possível preparar o vídeo."
        )

        logger.error(
            "Falha ao baixar vídeo | "
            "video_id=%s | arquivo=%s",
            video_id,
            video.get("arquivo"),
        )

        return None

    print(
        "\nVídeo preparado com sucesso."
    )

    print(
        f"Local: {caminho_local}"
    )

    logger.info(
        "Vídeo preparado | "
        "video_id=%s | arquivo=%s",
        video_id,
        video.get("arquivo"),
    )

    return caminho_local



def notificar_etapa(
    callback_etapa,
    etapa,
    status,
    mensagem=None,
    dados=None,
):
    """Notifica opcionalmente o andamento da publicação."""
    if callback_etapa is None:
        return

    callback_etapa(
        etapa=etapa,
        status=status,
        mensagem=mensagem,
        dados=dados or {},
    )


def processar_publicacao(
    video_id,
    video,
    privacidade,
    pedir_confirmacao=True,
    metadados_override=None,
    callback_etapa=None,
):
    notificar_etapa(
        callback_etapa,
        "PREPARACAO",
        "PROCESSANDO",
    )

    nome_arquivo = str(
        video.get(
            "arquivo",
            "",
        )
    ).strip()

    if not nome_arquivo:
        print(
            "\nO vídeo pendente não possui "
            "nome de arquivo."
        )

        print(
            f"ID interno: {video_id}"
        )

        logger.error(
            "Vídeo pendente sem nome de arquivo | "
            "video_id=%s",
            video_id,
        )

        notificar_etapa(
            callback_etapa,
            "PREPARACAO",
            "ERRO",
            mensagem="Vídeo pendente sem nome de arquivo",
        )

        return ResultadoPublicacao.falha(
            mensagem=(
                "Vídeo pendente sem nome "
                "de arquivo"
            ),
            video_id=video_id,
            etapa="validacao_video",
        )

    logger.info(
        "Publicação iniciada | "
        "video_id=%s | arquivo=%s | "
        "privacidade=%s",
        video_id,
        nome_arquivo,
        privacidade,
    )

    projeto = obter_projeto_ativo()

    if projeto is None:
        print(
            "\nNenhum projeto ativo."
        )

        logger.error(
            "Publicação interrompida | "
            "motivo=nenhum projeto ativo | "
            "video_id=%s",
            video_id,
        )

        notificar_etapa(
            callback_etapa,
            "PREPARACAO",
            "ERRO",
            mensagem="Nenhum projeto ativo",
        )

        return ResultadoPublicacao.falha(
            mensagem="Nenhum projeto ativo",
            video_id=video_id,
            etapa="projeto",
        )

    logger.info(
        "Projeto identificado | projeto=%s",
        projeto["nome"],
    )

    metadados = metadados_override

    if metadados is not None:
        logger.info(
            "Metadados recebidos pelo serviço | "
            "video_id=%s",
            video_id,
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

        notificar_etapa(
            callback_etapa,
            "PREPARACAO",
            "ERRO",
            mensagem="Metadados não encontrados",
        )

        return ResultadoPublicacao.falha(
            mensagem=(
                "Metadados não encontrados"
            ),
            video_id=video_id,
            etapa="metadados",
        )

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

        notificar_etapa(
            callback_etapa,
            "PREPARACAO",
            "ERRO",
            mensagem="Validação do canal do YouTube falhou",
        )

        return ResultadoPublicacao.falha(
            mensagem=(
                "Validação do canal "
                "do YouTube falhou"
            ),
            video_id=video_id,
            etapa="validacao_canal",
        )

    canal = (
        obter_canal_youtube_autenticado()
    )

    if canal is None:
        print(
            "\nNão foi possível identificar "
            "o canal autenticado."
        )

        logger.error(
            "Publicação interrompida | "
            "motivo=canal autenticado "
            "não identificado | "
            "video_id=%s",
            video_id,
        )

        notificar_etapa(
            callback_etapa,
            "PREPARACAO",
            "ERRO",
            mensagem="Canal autenticado não identificado",
        )

        return ResultadoPublicacao.falha(
            mensagem=(
                "Canal autenticado "
                "não identificado"
            ),
            video_id=video_id,
            etapa="canal",
        )

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

        notificar_etapa(
            callback_etapa,
            "PREPARACAO",
            "ERRO",
            mensagem="Não foi possível preparar o vídeo",
        )

        return ResultadoPublicacao.falha(
            mensagem=(
                "Não foi possível "
                "preparar o vídeo"
            ),
            video_id=video_id,
            etapa="download_video",
        )

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

            return ResultadoPublicacao.falha(
                mensagem=(
                    "Publicação cancelada "
                    "pelo usuário"
                ),
                video_id=video_id,
                etapa="confirmacao",
            )

    notificar_etapa(
        callback_etapa,
        "PREPARACAO",
        "CONCLUIDO",
    )

    notificar_etapa(
        callback_etapa,
        "UPLOAD",
        "PROCESSANDO",
    )

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

        notificar_etapa(
            callback_etapa,
            "UPLOAD",
            "ERRO",
            mensagem="Upload para o YouTube não concluído",
        )

        return ResultadoPublicacao.falha(
            mensagem=(
                "Upload para o YouTube "
                "não concluído"
            ),
            video_id=video_id,
            etapa="upload",
        )

    logger.info(
        "Upload concluído | "
        "video_id=%s | youtube_id=%s",
        video_id,
        youtube_id,
    )

    notificar_etapa(
        callback_etapa,
        "UPLOAD",
        "CONCLUIDO",
        dados={"youtube_id": youtube_id},
    )

    if playlist_id:
        notificar_etapa(
            callback_etapa,
            "PLAYLIST",
            "PROCESSANDO",
        )

    playlist_ok = adicionar_video_playlist(
        youtube_id=youtube_id,
        playlist_id=playlist_id,
    )

    if playlist_id:
        notificar_etapa(
            callback_etapa,
            "PLAYLIST",
            "CONCLUIDO" if playlist_ok else "ERRO",
            mensagem=(
                None if playlist_ok
                else "Falha ao aplicar playlist"
            ),
        )
    else:
        notificar_etapa(
            callback_etapa,
            "PLAYLIST",
            "IGNORADO",
            mensagem="Playlist não utilizada",
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
        notificar_etapa(
            callback_etapa,
            "THUMBNAIL",
            "PROCESSANDO",
        )

        thumbnail_ok = (
            definir_thumbnail_youtube(
                youtube_id=youtube_id,
                caminho_thumbnail=caminho_thumbnail,
            )
        )

    else:
        thumbnail_ok = True

    if caminho_thumbnail:
        notificar_etapa(
            callback_etapa,
            "THUMBNAIL",
            "CONCLUIDO" if thumbnail_ok else "ERRO",
            mensagem=(
                None if thumbnail_ok
                else "Falha ao aplicar thumbnail"
            ),
        )
    else:
        notificar_etapa(
            callback_etapa,
            "THUMBNAIL",
            "IGNORADO",
            mensagem="Thumbnail não utilizada",
        )

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

    notificar_etapa(
        callback_etapa,
        "DRIVE",
        "PROCESSANDO",
    )

    movido = mover_video_para_publicados(
        drive_id=video["drive_id"]
    )

    notificar_etapa(
        callback_etapa,
        "DRIVE",
        "CONCLUIDO" if movido else "ERRO",
        mensagem=(
            None if movido
            else "Falha ao mover vídeo para Publicados"
        ),
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

    notificar_etapa(
        callback_etapa,
        "FINALIZACAO",
        "PROCESSANDO",
    )

    notificar_etapa(
        callback_etapa,
        "FINALIZACAO",
        "CONCLUIDO",
    )

    logger.info(
        "Publicação concluída | "
        "video_id=%s | youtube_id=%s | "
        "playlist_ok=%s | thumbnail_ok=%s | "
        "drive_ok=%s",
        video_id,
        youtube_id,
        playlist_ok,
        thumbnail_ok,
        movido,
    )

    return ResultadoPublicacao.sucesso_publicacao(
        video_id=video_id,
        youtube_id=youtube_id,
        playlist_ok=playlist_ok,
        thumbnail_ok=thumbnail_ok,
        drive_ok=movido,
    )
