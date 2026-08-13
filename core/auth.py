from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import (
    ARQUIVO_CREDENTIALS,
    ARQUIVO_TOKEN_DRIVE,
    DRIVE_SCOPES,
    YOUTUBE_SCOPES,
)

from core.projetos import (
    obter_projeto_ativo,
    obter_token_youtube_projeto,
)


def obter_credenciais(
    arquivo_token: Path,
    scopes: list[str],
    nome_servico: str,
):
    credenciais = None

    arquivo_token.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if arquivo_token.exists():
        try:
            credenciais = (
                Credentials.from_authorized_user_file(
                    str(arquivo_token),
                    scopes,
                )
            )

        except (ValueError, OSError) as erro:
            print(
                f"Não foi possível ler o token "
                f"do {nome_servico}: {erro}"
            )

            credenciais = None

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
                    f"\nNão foi possível atualizar "
                    f"o token do {nome_servico}."
                )

                print(
                    f"Detalhes: {erro}"
                )

                print(
                    "\nSerá realizada uma nova "
                    "autenticação."
                )

                credenciais = None

        if not credenciais or not credenciais.valid:

            if not ARQUIVO_CREDENTIALS.exists():
                print(
                    "Arquivo credentials.json "
                    "não encontrado."
                )
                return None

            print(
                f"\nSerá aberta a autorização "
                f"do {nome_servico}."
            )

            flow = (
                InstalledAppFlow
                .from_client_secrets_file(
                    str(ARQUIVO_CREDENTIALS),
                    scopes,
                )
            )

            credenciais = flow.run_local_server(
                port=0
            )

        try:
            arquivo_token.write_text(
                credenciais.to_json(),
                encoding="utf-8",
            )

        except OSError as erro:
            print(
                f"Não foi possível salvar "
                f"o token do {nome_servico}: "
                f"{erro}"
            )

            return None

    return credenciais


def obter_credenciais_drive():
    return obter_credenciais(
        arquivo_token=ARQUIVO_TOKEN_DRIVE,
        scopes=DRIVE_SCOPES,
        nome_servico="Google Drive",
    )


def obter_credenciais_youtube():
    projeto = obter_projeto_ativo()

    if projeto is None:
        print(
            "\nNenhum projeto ativo."
        )
        return None

    arquivo_token = (
        obter_token_youtube_projeto()
    )

    return obter_credenciais(
        arquivo_token=arquivo_token,
        scopes=YOUTUBE_SCOPES,
        nome_servico=(
            f"YouTube - {projeto['nome']}"
        ),
    )