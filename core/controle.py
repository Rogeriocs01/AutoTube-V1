import json
from datetime import datetime

from config import ARQUIVO_CONTROLE, PASTA_DADOS

from core.drive import listar_videos_pendentes, baixar_video


def carregar_controle():
    if not ARQUIVO_CONTROLE.exists():
        return {}

    try:
        conteudo = ARQUIVO_CONTROLE.read_text(encoding="utf-8")

        if not conteudo.strip():
            return {}

        return json.loads(conteudo)

    except (json.JSONDecodeError, OSError) as erro:
        print(f"Erro ao carregar videos.json: {erro}")
        return {}


def salvar_controle(controle):
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)

    ARQUIVO_CONTROLE.write_text(
        json.dumps(
            controle,
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def criar_controle_videos():
    videos = listar_videos_pendentes()

    controle = {}

    for indice, video in enumerate(videos, start=1):

        video_id = f"YT_{indice:04d}"

        controle[video_id] = {
            "drive_id": video["id"],
            "arquivo": video["name"],
            "status": "pendente",
            "youtube_id": "",
            "data_publicacao": "",
        }

    salvar_controle(controle)

    print(f"Controle criado com {len(videos)} vídeos.")


def mostrar_resumo_controle():

    controle = carregar_controle()

    if not controle:
        print("\nO controle está vazio.")
        return

    total = len(controle)

    pendentes = sum(
        1
        for video in controle.values()
        if video["status"] == "pendente"
    )

    publicados = sum(
        1
        for video in controle.values()
        if video["status"] == "publicado"
    )

    erros = sum(
        1
        for video in controle.values()
        if video["status"] == "erro"
    )

    print("\n===== RESUMO DO CONTROLE =====")
    print(f"Total de vídeos: {total}")
    print(f"Pendentes: {pendentes}")
    print(f"Publicados: {publicados}")
    print(f"Erros: {erros}")


def obter_proximo_video_pendente():

    controle = carregar_controle()

    for video_id, video in controle.items():

        if video["status"] == "pendente":
            return video_id, video

    return None, None


def mostrar_proximo_video():

    video_id, video = obter_proximo_video_pendente()

    if video is None:
        print("\nNenhum vídeo pendente encontrado.")
        return

    print("\n===== PRÓXIMO VÍDEO =====")
    print(f"ID interno : {video_id}")
    print(f"Arquivo    : {video['arquivo']}")
    print(f"Drive ID   : {video['drive_id']}")
    print(f"Status     : {video['status']}")
    print("==========================")


def baixar_proximo_video():

    video_id, video = obter_proximo_video_pendente()

    if video is None:
        print("\nNenhum vídeo pendente encontrado.")
        return None

    print("\n===== DOWNLOAD DO PRÓXIMO VÍDEO =====")
    print(f"ID interno : {video_id}")
    print(f"Arquivo    : {video['arquivo']}")
    print("=====================================")

    caminho = baixar_video(
        drive_id=video["drive_id"],
        nome_arquivo=video["arquivo"],
    )

    if caminho:
        print("\nDownload realizado com sucesso.")
        print("Status do vídeo permanece como 'pendente'.")

    return caminho

def registrar_video_publicado(video_id, youtube_id):
    controle = carregar_controle()

    if video_id not in controle:
        print(f"Vídeo não encontrado no controle: {video_id}")
        return False

    controle[video_id]["status"] = "publicado"
    controle[video_id]["youtube_id"] = youtube_id
    controle[video_id]["data_publicacao"] = datetime.now().isoformat(
        timespec="seconds"
    )

    salvar_controle(controle)

    print("videos.json atualizado com sucesso.")
    return True