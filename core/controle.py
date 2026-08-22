import json
from datetime import datetime

from core.drive import (
    listar_videos_pendentes,
    baixar_video,
)

from core.projetos import (
    obter_arquivo_controle_projeto,
    obter_pasta_dados_projeto,
)


def carregar_controle():
    arquivo_controle = (
        obter_arquivo_controle_projeto()
    )

    if not arquivo_controle.exists():
        return {}

    try:
        conteudo = arquivo_controle.read_text(
            encoding="utf-8"
        )

        if not conteudo.strip():
            return {}

        return json.loads(conteudo)

    except (json.JSONDecodeError, OSError) as erro:
        print(
            f"Erro ao carregar videos.json: {erro}"
        )
        return {}


def salvar_controle(controle):
    pasta_dados = (
        obter_pasta_dados_projeto()
    )

    arquivo_controle = (
        obter_arquivo_controle_projeto()
    )

    pasta_dados.mkdir(
        parents=True,
        exist_ok=True,
    )

    arquivo_controle.write_text(
        json.dumps(
            controle,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def selecionar_tipo_conteudo(nome_arquivo):
    """
    Pergunta se o vídeo é Short ou vídeo longo.

    Retorna:
        "short"
        "longo"

    Retorna None quando o usuário cancela.
    """

    while True:
        print(
            "\n===== CLASSIFICAR CONTEÚDO ====="
        )
        print(
            f"Arquivo: {nome_arquivo}"
        )
        print("")
        print("1 - Short")
        print("2 - Vídeo longo")
        print("0 - Cancelar")
        print(
            "================================"
        )

        opcao = input(
            "\nEscolha uma opção: "
        ).strip()

        if opcao == "1":
            return "short"

        if opcao == "2":
            return "longo"

        if opcao == "0":
            print(
                "\nSincronização cancelada."
            )
            return None

        print(
            "\nOpção inválida. "
            "Escolha 1, 2 ou 0."
        )


def obter_maior_numero_id(controle):
    """
    Procura o maior número já utilizado
    em IDs do formato YT_0001.
    """

    maior_numero = 0

    for video_id in controle.keys():
        if not video_id.startswith("YT_"):
            continue

        try:
            numero = int(
                video_id.split("_", 1)[1]
            )

        except (ValueError, IndexError):
            continue

        if numero > maior_numero:
            maior_numero = numero

    return maior_numero


def criar_controle_videos():
    """
    Sincroniza a pasta Pendentes do projeto ativo
    com o videos.json.

    O histórico existente é preservado.
    Apenas vídeos novos são adicionados.
    """

    videos_drive = listar_videos_pendentes()
    controle_atual = carregar_controle()

    drive_ids_existentes = {
        video.get("drive_id")
        for video in controle_atual.values()
        if video.get("drive_id")
    }

    videos_novos = [
        video
        for video in videos_drive
        if video["id"] not in drive_ids_existentes
    ]

    if not videos_novos:
        print(
            "\nNenhum vídeo novo encontrado "
            "na pasta Pendentes."
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

    maior_numero = obter_maior_numero_id(
        controle_atual
    )

    proximo_numero = maior_numero + 1

    novo_controle = (
        controle_atual.copy()
    )

    novos_registros = []

    for video in videos_novos:
        tipo_conteudo = (
            selecionar_tipo_conteudo(
                video["name"]
            )
        )

        if tipo_conteudo is None:
            print(
                "\nNenhuma alteração foi salva."
            )
            return

        video_id = (
            f"YT_{proximo_numero:04d}"
        )

        registro = {
            "drive_id": video["id"],
            "arquivo": video["name"],
            "tipo_conteudo": tipo_conteudo,
            "status": "pendente",
            "youtube_id": "",
            "data_publicacao": "",
        }

        novo_controle[
            video_id
        ] = registro

        novos_registros.append(
            (
                video_id,
                registro,
            )
        )

        nome_tipo = (
            "SHORT"
            if tipo_conteudo == "short"
            else "LONGO"
        )

        print(
            f"\nRegistrado: {video_id}"
        )
        print(
            f"Arquivo    : {video['name']}"
        )
        print(
            f"Tipo       : {nome_tipo}"
        )

        proximo_numero += 1

    salvar_controle(
        novo_controle
    )

    print(
        "\n===== SINCRONIZAÇÃO CONCLUÍDA ====="
    )

    print(
        f"Novos vídeos     : "
        f"{len(novos_registros)}"
    )

    print(
        f"Total no controle: "
        f"{len(novo_controle)}"
    )

    print(
        "===================================="
    )


def mostrar_resumo_controle():
    controle = carregar_controle()

    if not controle:
        print(
            "\nO controle está vazio."
        )
        return

    total = len(controle)

    pendentes = sum(
        1
        for video in controle.values()
        if video.get("status") == "pendente"
    )

    publicados = sum(
        1
        for video in controle.values()
        if video.get("status") == "publicado"
    )

    erros = sum(
        1
        for video in controle.values()
        if video.get("status") == "erro"
    )

    shorts = sum(
        1
        for video in controle.values()
        if video.get("tipo_conteudo") == "short"
    )

    longos = sum(
        1
        for video in controle.values()
        if video.get("tipo_conteudo") == "longo"
    )

    print(
        "\n===== RESUMO DO CONTROLE ====="
    )

    print(
        f"Total de vídeos: {total}"
    )

    print(
        f"Pendentes       : {pendentes}"
    )

    print(
        f"Publicados      : {publicados}"
    )

    print(
        f"Erros           : {erros}"
    )

    print(
        f"Shorts          : {shorts}"
    )

    print(
        f"Vídeos longos   : {longos}"
    )


def obter_proximo_video_pendente():
    controle = carregar_controle()

    for video_id, video in controle.items():
        if video.get("status") == "pendente":
            return video_id, video

    return None, None


def mostrar_proximo_video():
    video_id, video = (
        obter_proximo_video_pendente()
    )

    if video is None:
        print(
            "\nNenhum vídeo pendente encontrado."
        )
        return

    tipo_conteudo = video.get(
        "tipo_conteudo",
        "não definido",
    )

    if tipo_conteudo == "short":
        nome_tipo = "SHORT"

    elif tipo_conteudo == "longo":
        nome_tipo = "LONGO"

    else:
        nome_tipo = "NÃO DEFINIDO"

    print(
        "\n===== PRÓXIMO VÍDEO ====="
    )

    print(
        f"ID interno : {video_id}"
    )

    print(
        f"Arquivo    : {video['arquivo']}"
    )

    print(
        f"Tipo       : {nome_tipo}"
    )

    print(
        f"Drive ID   : {video['drive_id']}"
    )

    print(
        f"Status     : {video['status']}"
    )

    print(
        "=========================="
    )


def baixar_proximo_video():
    video_id, video = (
        obter_proximo_video_pendente()
    )

    if video is None:
        print(
            "\nNenhum vídeo pendente encontrado."
        )
        return None

    print(
        "\n===== DOWNLOAD DO "
        "PRÓXIMO VÍDEO ====="
    )

    print(
        f"ID interno : {video_id}"
    )

    print(
        f"Arquivo    : {video['arquivo']}"
    )

    print(
        "====================================="
    )

    caminho = baixar_video(
        drive_id=video["drive_id"],
        nome_arquivo=video["arquivo"],
    )

    if caminho:
        print(
            "\nDownload realizado com sucesso."
        )

        print(
            "Status do vídeo permanece "
            "como 'pendente'."
        )

    return caminho

def selecionar_video_pendente():
    """
    Exibe todos os vídeos pendentes do projeto ativo
    e permite escolher um deles.

    Retorna:
        video_id, video

    Retorna:
        None, None

    quando o usuário cancela.
    """

    controle = carregar_controle()

    pendentes = []

    for video_id, video in controle.items():
        if video.get("status") == "pendente":
            pendentes.append(
                {
                    "video_id": video_id,
                    "video": video,
                }
            )

    if not pendentes:
        print(
            "\nNenhum vídeo pendente encontrado."
        )
        return None, None

    print(
        "\n===== VÍDEOS PENDENTES ====="
    )

    for indice, item in enumerate(
        pendentes,
        start=1,
    ):
        video = item["video"]

        tipo = video.get(
            "tipo_conteudo",
            "",
        )

        if tipo == "short":
            nome_tipo = "SHORT"

        elif tipo == "longo":
            nome_tipo = "LONGO"

        else:
            nome_tipo = "N/D"

        print(
            f"{indice} - "
            f"[{nome_tipo}] "
            f"{video.get('arquivo', 'Sem nome')}"
        )

    print("")
    print("0 - Cancelar")
    print(
        "============================"
    )

    while True:
        escolha = input(
            "\nEscolha o vídeo: "
        ).strip()

        if escolha == "0":
            print(
                "\nSeleção cancelada."
            )
            return None, None

        if not escolha.isdigit():
            print(
                "\nOpção inválida."
            )
            continue

        indice = int(escolha) - 1

        if (
            indice < 0
            or indice >= len(pendentes)
        ):
            print(
                "\nOpção inválida."
            )
            continue

        escolhido = pendentes[indice]

        return (
            escolhido["video_id"],
            escolhido["video"],
        )


def registrar_video_publicado(
    video_id,
    youtube_id,
):
    controle = carregar_controle()

    if video_id not in controle:
        print(
            "Vídeo não encontrado no controle: "
            f"{video_id}"
        )
        return False

    controle[
        video_id
    ]["status"] = "publicado"

    controle[
        video_id
    ]["youtube_id"] = youtube_id

    controle[
        video_id
    ][
        "data_publicacao"
    ] = datetime.now().isoformat(
        timespec="seconds"
    )

    salvar_controle(
        controle
    )

    print(
        "videos.json atualizado com sucesso."
    )

    return True