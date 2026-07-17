from core.controle import (
    obter_proximo_video_pendente,
    registrar_video_publicado,
)
from core.drive import (
    baixar_video,
    mover_video_para_publicados,
)
from core.metadados import buscar_metadados
from core.youtube import publicar_video


NOMES_PRIVACIDADE = {
    "private": "PRIVADO",
    "public": "PÚBLICO",
    "unlisted": "NÃO LISTADO",
}


def selecionar_privacidade():
    """
    Permite escolher a visibilidade dos vídeos no YouTube.

    Retorna:
        private
        public
        unlisted

    Retorna None quando o usuário cancela.
    """
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
            return None

        print("\nOpção inválida. Escolha 1, 2, 3 ou 0.")


def selecionar_quantidade_lote():
    """
    Permite escolher a quantidade de vídeos do lote.

    Retorna:
        2
        3

    Retorna None quando o usuário cancela.
    """
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
            return None

        print("\nOpção inválida. Escolha 1, 2 ou 0.")


def excluir_arquivo_temporario(caminho_local):
    """
    Exclui o arquivo baixado da pasta temporária.
    """
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


def preparar_proximo_video(video_id, video):
    """
    Baixa ou localiza na pasta temporária o vídeo
    que será enviado ao YouTube.
    """
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
        return None

    print("\nVídeo preparado com sucesso.")
    print(f"Local: {caminho_local}")

    return caminho_local


def processar_publicacao(
    video_id,
    video,
    privacidade,
    pedir_confirmacao=True,
):
    """
    Executa o processo completo de publicação de um vídeo.

    Retorna True quando todo o processo é concluído.
    Retorna False quando ocorre cancelamento ou erro.
    """
    nome_arquivo = str(
        video.get("arquivo", "")
    ).strip()

    if not nome_arquivo:
        print("\nO vídeo pendente não possui nome de arquivo.")
        print(f"ID interno: {video_id}")
        return False

    metadados = buscar_metadados(nome_arquivo)

    if metadados is None:
        print("\n===== METADADOS NÃO ENCONTRADOS =====")
        print(f"ID interno : {video_id}")
        print(f"Arquivo    : {nome_arquivo}")
        print(
            "\nO vídeo permanece pendente e continuará "
            "disponível para uma próxima tentativa."
        )
        print("=====================================")
        return False

    caminho_local = preparar_proximo_video(
        video_id=video_id,
        video=video,
    )

    if caminho_local is None:
        return False

    nome_privacidade = NOMES_PRIVACIDADE.get(
        privacidade,
        privacidade.upper(),
    )

    print("\n===== DADOS DA PUBLICAÇÃO =====")
    print(f"ID interno   : {video_id}")
    print(f"Arquivo      : {caminho_local.name}")
    print(f"Título       : {metadados['titulo']}")
    print(f"Visibilidade : {nome_privacidade}")
    print("===============================")

    if pedir_confirmacao:
        confirmar = input(
            f"\nPublicar este vídeo como "
            f"{nome_privacidade}? [S/N]: "
        ).strip().lower()

        if confirmar != "s":
            print("\nPublicação cancelada.")
            excluir_arquivo_temporario(caminho_local)
            return False

    youtube_id = publicar_video(
        caminho_video=caminho_local,
        titulo=metadados["titulo"],
        descricao=metadados["descricao"],
        privacidade=privacidade,
    )

    if youtube_id is None:
        print("\nO upload não foi concluído.")
        return False

    registrado = registrar_video_publicado(
        video_id=video_id,
        youtube_id=youtube_id,
    )

    if not registrado:
        print(
            "\nO vídeo foi enviado ao YouTube, mas houve erro "
            "ao atualizar o videos.json."
        )
        return False

    movido = mover_video_para_publicados(
        drive_id=video["drive_id"]
    )

    if not movido:
        print(
            "\nO vídeo foi publicado e registrado, mas não foi "
            "movido para a pasta Publicados."
        )
        return False

    excluir_arquivo_temporario(caminho_local)

    print("\n===== PROCESSO CONCLUÍDO =====")
    print(f"ID interno   : {video_id}")
    print(f"YouTube ID   : {youtube_id}")
    print(f"Título       : {metadados['titulo']}")
    print(f"Visibilidade : {nome_privacidade}")
    print("Status       : publicado")
    print("Drive        : movido para Publicados")
    print("Temp         : limpa")
    print("==============================")

    return True


def publicar_proximo_video():
    """
    Publica individualmente o próximo vídeo pendente.
    """
    video_id, video = obter_proximo_video_pendente()

    if video is None:
        print("\nNenhum vídeo pendente encontrado.")
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
    """
    Publica automaticamente um lote de 2 ou 3 vídeos.

    A quantidade, a visibilidade e a confirmação são
    solicitadas apenas uma vez.

    O lote é interrompido ao ocorrer qualquer erro ou
    quando o próximo vídeo não possui metadados.
    """
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
        print("\nPublicação em lote cancelada.")
        return

    publicados = 0
    motivo_interrupcao = None

    print("\n===== INICIANDO PUBLICAÇÃO EM LOTE =====")

    for numero_atual in range(1, quantidade + 1):
        print(
            f"\n===== VÍDEO {numero_atual} "
            f"DE {quantidade} ====="
        )

        video_id, video = obter_proximo_video_pendente()

        if video is None:
            motivo_interrupcao = (
                "Não existem mais vídeos pendentes."
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
            break

        publicados += 1

    print("\n===== RESUMO DO LOTE =====")
    print(f"Solicitados : {quantidade}")
    print(f"Publicados  : {publicados}")

    if motivo_interrupcao is None:
        print("Resultado   : lote concluído com sucesso")
    else:
        print("Resultado   : lote interrompido")
        print(f"Motivo      : {motivo_interrupcao}")

    print("==========================")