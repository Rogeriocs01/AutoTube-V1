import json
import platform
from pathlib import Path

from config import (
    BASE_DIR,
    PASTA_DADOS,
    PASTA_LOGS,
    PASTA_TEMP,
    ARQUIVO_CREDENTIALS,
    ARQUIVO_TOKEN_DRIVE,
)

from core.logger import obter_logger

from core.projetos import (
    PASTA_PROJETOS,
    ARQUIVO_PROJETOS,
    ARQUIVO_PROJETO_ATIVO,
    obter_projeto_ativo,
)


logger = obter_logger()


def mostrar_status(status, mensagem):
    print(
        f"[{status}] {mensagem}"
    )


def verificar_pasta(
    pasta,
    nome,
    criar=False,
):
    if pasta.exists():
        mostrar_status(
            "OK",
            f"{nome}: {pasta}",
        )

        return True

    if criar:
        try:
            pasta.mkdir(
                parents=True,
                exist_ok=True,
            )

            mostrar_status(
                "AVISO",
                f"{nome} não existia e foi criada: {pasta}",
            )

            return True

        except OSError as erro:
            mostrar_status(
                "ERRO",
                f"{nome} não pôde ser criada: {erro}",
            )

            return False

    mostrar_status(
        "ERRO",
        f"{nome} não encontrada: {pasta}",
    )

    return False


def verificar_arquivo(
    arquivo,
    nome,
    obrigatorio=True,
):
    if arquivo.exists():
        mostrar_status(
            "OK",
            f"{nome}: encontrado",
        )

        return True

    if obrigatorio:
        mostrar_status(
            "ERRO",
            f"{nome}: não encontrado",
        )

        return False

    mostrar_status(
        "AVISO",
        f"{nome}: não encontrado",
    )

    return True


def verificar_json(
    arquivo,
    nome,
):
    if not arquivo.exists():
        mostrar_status(
            "ERRO",
            f"{nome}: arquivo não encontrado",
        )

        return False

    try:
        conteudo = arquivo.read_text(
            encoding="utf-8",
        )

        json.loads(
            conteudo
        )

        mostrar_status(
            "OK",
            f"{nome}: JSON válido",
        )

        return True

    except json.JSONDecodeError as erro:
        mostrar_status(
            "ERRO",
            f"{nome}: JSON inválido ({erro})",
        )

        return False

    except OSError as erro:
        mostrar_status(
            "ERRO",
            f"{nome}: não pôde ser lido ({erro})",
        )

        return False


def verificar_escrita(
    pasta,
    nome,
):
    try:
        pasta.mkdir(
            parents=True,
            exist_ok=True,
        )

        arquivo_teste = (
            pasta
            / ".autotube_write_test"
        )

        arquivo_teste.write_text(
            "teste",
            encoding="utf-8",
        )

        arquivo_teste.unlink()

        mostrar_status(
            "OK",
            f"Permissão de escrita em {nome}",
        )

        return True

    except OSError as erro:
        mostrar_status(
            "ERRO",
            f"Sem permissão de escrita em "
            f"{nome}: {erro}",
        )

        return False


def verificar_projeto_ativo():
    projeto = obter_projeto_ativo()

    if projeto is None:
        mostrar_status(
            "ERRO",
            "Nenhum projeto ativo",
        )

        return False, None

    projeto_id = projeto.get(
        "id"
    )

    nome = projeto.get(
        "nome",
        "Sem nome",
    )

    mostrar_status(
        "OK",
        f"Projeto ativo: {nome} ({projeto_id})",
    )

    return True, projeto


def verificar_estrutura_projeto(
    projeto,
):
    resultado = True

    projeto_id = projeto["id"]

    pasta_dados = (
        PASTA_DADOS
        / projeto_id
    )

    arquivo_videos = (
        pasta_dados
        / "videos.json"
    )

    arquivo_metadados = (
        pasta_dados
        / "metadados.json"
    )

    pasta_credenciais = (
        BASE_DIR
        / "credenciais"
        / projeto_id
    )

    token_youtube = (
        pasta_credenciais
        / "token_youtube.json"
    )

    if verificar_pasta(
        pasta_dados,
        "Pasta de dados do projeto",
        criar=False,
    ) is False:
        resultado = False

    if verificar_arquivo(
        arquivo_videos,
        "videos.json",
    ) is False:
        resultado = False

    if verificar_arquivo(
        arquivo_metadados,
        "metadados.json",
    ) is False:
        resultado = False

    plataformas = projeto.get(
        "plataformas",
        {}
    )

    youtube = plataformas.get(
        "youtube",
        {}
    )

    youtube_ativo = youtube.get(
        "ativo",
        False,
    )

    if youtube_ativo:
        mostrar_status(
            "OK",
            "YouTube está ativo no projeto",
        )

        if verificar_arquivo(
            token_youtube,
            "Token YouTube do projeto",
        ) is False:
            resultado = False

    else:
        mostrar_status(
            "AVISO",
            "YouTube está inativo no projeto",
        )

    return resultado


def executar_diagnostico():
    logger.info(
        "Diagnóstico do ambiente iniciado"
    )

    erros = 0
    avisos = 0

    print(
        "\n========================================"
    )
    print(
        "       DIAGNÓSTICO DO AUTOTUBE"
    )
    print(
        "========================================"
    )

    print()
    print("SISTEMA")

    print(
        f"Python............... "
        f"{platform.python_version()}"
    )

    print(
        f"Sistema.............. "
        f"{platform.system()} "
        f"{platform.release()}"
    )

    print(
        f"Diretório base....... "
        f"{BASE_DIR}"
    )

    print()
    print("ESTRUTURA")

    verificacoes_pastas = [
        (
            PASTA_DADOS,
            "Pasta dados",
            True,
        ),
        (
            PASTA_LOGS,
            "Pasta logs",
            True,
        ),
        (
            PASTA_TEMP,
            "Pasta temp",
            True,
        ),
        (
            PASTA_PROJETOS,
            "Pasta projetos",
            True,
        ),
    ]

    for pasta, nome, criar in verificacoes_pastas:
        existia = pasta.exists()

        resultado = verificar_pasta(
            pasta,
            nome,
            criar=criar,
        )

        if not resultado:
            erros += 1

        elif not existia:
            avisos += 1

    print()
    print("CONFIGURAÇÃO")

    if not verificar_json(
        ARQUIVO_PROJETOS,
        "projetos.json",
    ):
        erros += 1

    if not verificar_json(
        ARQUIVO_PROJETO_ATIVO,
        "projeto_ativo.json",
    ):
        erros += 1

    print()
    print("GOOGLE")

    if not verificar_arquivo(
        ARQUIVO_CREDENTIALS,
        "credentials.json",
    ):
        erros += 1

    if not verificar_arquivo(
        ARQUIVO_TOKEN_DRIVE,
        "Token Google Drive",
    ):
        erros += 1

    print()
    print("PROJETO ATIVO")

    projeto_ok, projeto = (
        verificar_projeto_ativo()
    )

    if not projeto_ok:
        erros += 1

    elif not verificar_estrutura_projeto(
        projeto
    ):
        erros += 1

    print()
    print("ARMAZENAMENTO")

    if not verificar_escrita(
        PASTA_TEMP,
        "temp",
    ):
        erros += 1

    if not verificar_escrita(
        PASTA_LOGS,
        "logs",
    ):
        erros += 1

    print()
    print(
        "----------------------------------------"
    )

    if erros == 0:
        if avisos == 0:
            resultado_texto = (
                "AMBIENTE SAUDÁVEL"
            )
        else:
            resultado_texto = (
                "AMBIENTE SAUDÁVEL COM AVISOS"
            )

    else:
        resultado_texto = (
            "ATENÇÃO NECESSÁRIA"
        )

    print(
        f"Resultado: {resultado_texto}"
    )

    print(
        f"Erros    : {erros}"
    )

    print(
        f"Avisos   : {avisos}"
    )

    print(
        "========================================"
    )

    logger.info(
        "Diagnóstico concluído | "
        "resultado=%s | erros=%s | avisos=%s",
        resultado_texto,
        erros,
        avisos,
    )

    return erros == 0
