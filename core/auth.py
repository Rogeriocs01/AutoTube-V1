from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import (
    ARQUIVO_CREDENTIALS,
    ARQUIVO_TOKEN_DRIVE,
    ARQUIVO_TOKEN_YOUTUBE,
    DRIVE_SCOPES,
    YOUTUBE_SCOPES,
)


def obter_credenciais(
    arquivo_token: Path,
    scopes: list[str],
    nome_servico: str,
):
    credenciais = None

    if arquivo_token.exists():
        try:
            credenciais = Credentials.from_authorized_user_file(
                str(arquivo_token),
                scopes,
            )
        except (ValueError, OSError) as erro:
            print(
                f"Não foi possível ler o token do {nome_servico}: {erro}"
            )
            return None

    if not credenciais or not credenciais.valid:
        if (
            credenciais
            and credenciais.expired
            and credenciais.refresh_token
        ):
            try:
                credenciais.refresh(Request())
            except Exception as erro:
                print(
                    f"Não foi possível atualizar o token do "
                    f"{nome_servico}: {erro}"
                )
                return None

        else:
            if not ARQUIVO_CREDENTIALS.exists():
                print("Arquivo credentials.json não encontrado.")
                return None

            print(
                f"\nSerá aberta a autorização do {nome_servico}."
            )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(ARQUIVO_CREDENTIALS),
                scopes,
            )

            credenciais = flow.run_local_server(port=0)

        arquivo_token.write_text(
            credenciais.to_json(),
            encoding="utf-8",
        )

    return credenciais


def obter_credenciais_drive():
    return obter_credenciais(
        arquivo_token=ARQUIVO_TOKEN_DRIVE,
        scopes=DRIVE_SCOPES,
        nome_servico="Google Drive",
    )


def obter_credenciais_youtube():
    return obter_credenciais(
        arquivo_token=ARQUIVO_TOKEN_YOUTUBE,
        scopes=YOUTUBE_SCOPES,
        nome_servico="YouTube",
    )