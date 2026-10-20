"""Fingerprint verificável para solicitações de publicação."""

import hashlib
import json


CAMPOS_CONTEUDO_SNAPSHOT = (
    "id",
    "projeto_id",
    "id_legado",
    "tipo",
    "nome_arquivo",
    "origem",
    "conteudo_pai_id",
    "drive_file_id",
    "status",
)

CAMPOS_METADADOS_SNAPSHOT = (
    "conteudo_id",
    "titulo",
    "descricao",
    "hashtags",
    "playlist_id",
    "playlist_nome",
    "idioma",
    "categoria",
    "thumbnail_drive_id",
    "thumbnail_nome_arquivo",
)

CAMPOS_PARAMETROS_SNAPSHOT = (
    "conteudo_id",
    "privacidade",
    "canal_id",
    "prioridade",
    "plataforma",
    "agendado_para",
)


def _selecionar_campos(dados, campos):
    return {
        campo: dados.get(campo)
        for campo in campos
    }


def calcular_fingerprint_snapshot(conteudo, metadados, parametros):
    """Calcula SHA-256 sobre uma representação canônica e não volátil."""

    snapshot = {
        "versao": 1,
        "conteudo": _selecionar_campos(
            conteudo,
            CAMPOS_CONTEUDO_SNAPSHOT,
        ),
        "metadados": _selecionar_campos(
            metadados,
            CAMPOS_METADADOS_SNAPSHOT,
        ),
        "parametros": _selecionar_campos(
            parametros,
            CAMPOS_PARAMETROS_SNAPSHOT,
        ),
    }
    serializado = json.dumps(
        snapshot,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(serializado).hexdigest()
