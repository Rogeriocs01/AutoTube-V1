from pathlib import Path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import (
    ARQUIVO_CONTROLE,
    ARQUIVO_CREDENTIALS,
    ARQUIVO_TOKEN,
    CANAL_YOUTUBE_ID,
    EXTENSOES_VIDEO,
    PASTA_DADOS,
    PASTA_PENDENTES_ID,
    SCOPES,
)



def conectar_drive():
    creds = None

    if ARQUIVO_TOKEN.exists():
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(ARQUIVO_CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)

        ARQUIVO_TOKEN.write_text(creds.to_json(), encoding="utf-8")

    return build("drive", "v3", credentials=creds)


def listar_videos_drive():
    service = conectar_drive()

    query = f"'{PASTA_PENDENTES_ID}' in parents and trashed = false"

    resultado = service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        pageSize=1000
    ).execute()

    arquivos = resultado.get("files", [])

    videos = []
    for arquivo in arquivos:
        extensao = Path(arquivo["name"]).suffix.lower()
        if extensao in EXTENSOES_VIDEO:
            videos.append(arquivo)

    videos = sorted(videos, key=lambda x: x["name"])
    return videos


def criar_controle_videos():
    videos = listar_videos_drive()

    ARQUIVO_CONTROLE.parent.mkdir(exist_ok=True)

    controle = {}

    for indice, video in enumerate(videos, start=1):
        video_id = f"YT_{indice:04d}"
        controle[video_id] = {
            "drive_id": video["id"],
            "arquivo": video["name"],
            "status": "pendente",
            "youtube_id": "",
            "data_publicacao": ""
        }

    ARQUIVO_CONTROLE.write_text(
        json.dumps(controle, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    print(f"Controle criado com {len(videos)} vídeos.")
def mostrar_resumo_controle():
    if not ARQUIVO_CONTROLE.exists():
        print("Arquivo videos.json ainda não existe.")
        return

    dados = json.loads(ARQUIVO_CONTROLE.read_text(encoding="utf-8"))

    total = len(dados)
    pendentes = sum(1 for v in dados.values() if v["status"] == "pendente")
    publicados = sum(1 for v in dados.values() if v["status"] == "publicado")
    erros = sum(1 for v in dados.values() if v["status"] == "erro")

    print("\n===== RESUMO DO CONTROLE =====")
    print(f"Total de vídeos: {total}")
    print(f"Pendentes: {pendentes}")
    print(f"Publicados: {publicados}")
    print(f"Erros: {erros}")    

def listar_canais_youtube():
    service = conectar_drive()

    youtube = build("youtube", "v3", credentials=service._http.credentials)

    resposta = youtube.channels().list(
        part="snippet,id",
        mine=True
    ).execute()

    canais = resposta.get("items", [])

    print("\n===== CANAIS DISPONÍVEIS NA API =====")

    if not canais:
        print("Nenhum canal encontrado.")
        return

    for canal in canais:
        print(f"Nome: {canal['snippet']['title']}")
        print(f"ID: {canal['id']}")
        print("-" * 40)    

def obter_proximo_video_pendente():
    if not ARQUIVO_CONTROLE.exists():
        print("\nO arquivo dados/videos.json ainda não existe.")
        return None, None

    try:
        controle = json.loads(
            ARQUIVO_CONTROLE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        print("\nErro: o arquivo videos.json está vazio ou corrompido.")
        return None, None

    for video_id, video in controle.items():
        if video.get("status") == "pendente":
            return video_id, video

    return None, None

def mostrar_proximo_video():
    video_id, video = obter_proximo_video_pendente()

    if video is None:
        print("\nNenhum vídeo pendente encontrado.")
        return

    print("\n===== PRÓXIMO VÍDEO =====")
    print(f"ID interno: {video_id}")
    print(f"Arquivo: {video.get('arquivo', 'Não informado')}")
    print(f"Drive ID: {video.get('drive_id', 'Não informado')}")
    print(f"Status: {video.get('status', 'Não informado')}")
    print("==========================")        

def mostrar_menu():
    while True:
        print("\n======================")
        print("      AUTOTUBE V1")
        print("======================")
        print("1 - Testar conexão com Google Drive")
        print("2 - Listar vídeos pendentes")
        print("3 - Criar controle videos.json")
        print("4 - Ver resumo do controle")
        print("5 - Listar canais do YouTube")
        print("6 - Mostrar próximo vídeo")
        print("0 - Sair")

        opcao = input("\nEscolha uma opção: ")

        if opcao == "1":
            conectar_drive()
            print("Conectado ao Google Drive com sucesso!")

        elif opcao == "2":
            videos = listar_videos_drive()
            print(f"\nVídeos encontrados: {len(videos)}")
            for video in videos:
                print("-", video["name"])

        elif opcao == "3":
            criar_controle_videos()

        elif opcao == "4":
             mostrar_resumo_controle()   

        elif opcao == "5":
            listar_canais_youtube() 

        elif opcao == "6":
            mostrar_proximo_video()    

        elif opcao == "0":
            print("Saindo...")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    mostrar_menu()