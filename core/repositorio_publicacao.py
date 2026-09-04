from datetime import datetime
from uuid import uuid4

from core.database import conectar_banco


def agora_iso():
    """
    Retorna data/hora atual
    em formato ISO.
    """

    return datetime.now().isoformat(
        timespec="seconds"
    )


def gerar_id_publicacao():
    """
    Gera um ID global para uma publicação.

    Exemplo:

    pub_a12b34...
    """

    return (
        "pub_"
        + uuid4().hex
    )


# ============================================================
# PUBLICAÇÕES
# ============================================================


def criar_publicacao(
    conteudo_id,
    plataforma,
    canal_id=None,
    privacidade=None,
    status="AGUARDANDO",
    publicacao_id=None,
):
    """
    Cria uma publicação para um conteúdo.

    Um mesmo conteúdo poderá possuir
    várias publicações em diferentes
    plataformas.
    """

    if publicacao_id is None:
        publicacao_id = (
            gerar_id_publicacao()
        )

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            INSERT INTO publicacoes (
                id,
                conteudo_id,
                plataforma,
                canal_id,
                privacidade,
                status,
                data_criacao,
                data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                publicacao_id,
                conteudo_id,
                plataforma,
                canal_id,
                privacidade,
                status,
                agora_iso(),
                agora_iso(),
            ),
        )

        conexao.commit()

        return publicacao_id

    finally:
        conexao.close()


def obter_publicacao(
    publicacao_id,
):
    """
    Retorna uma publicação pelo ID.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM publicacoes
            WHERE id = ?;
            """,
            (
                publicacao_id,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()


def listar_publicacoes(
    conteudo_id=None,
    plataforma=None,
    status=None,
):
    """
    Lista publicações com filtros opcionais.
    """

    conexao = conectar_banco()

    try:
        query = """
            SELECT *
            FROM publicacoes
            WHERE 1 = 1
        """

        parametros = []

        if conteudo_id is not None:
            query += """
                AND conteudo_id = ?
            """

            parametros.append(
                conteudo_id
            )

        if plataforma is not None:
            query += """
                AND plataforma = ?
            """

            parametros.append(
                plataforma
            )

        if status is not None:
            query += """
                AND status = ?
            """

            parametros.append(
                status
            )

        query += """
            ORDER BY data_criacao;
        """

        cursor = conexao.execute(
            query,
            parametros,
        )

        return [
            dict(linha)
            for linha in cursor.fetchall()
        ]

    finally:
        conexao.close()


def atualizar_publicacao(
    publicacao_id,
    status=None,
    external_id=None,
    url=None,
    data_inicio=None,
    data_conclusao=None,
):
    """
    Atualiza informações de uma publicação.

    Apenas os campos informados
    serão alterados.
    """

    campos = []
    valores = []

    if status is not None:
        campos.append(
            "status = ?"
        )

        valores.append(
            status
        )

    if external_id is not None:
        campos.append(
            "external_id = ?"
        )

        valores.append(
            external_id
        )

    if url is not None:
        campos.append(
            "url = ?"
        )

        valores.append(
            url
        )

    if data_inicio is not None:
        campos.append(
            "data_inicio = ?"
        )

        valores.append(
            data_inicio
        )

    if data_conclusao is not None:
        campos.append(
            "data_conclusao = ?"
        )

        valores.append(
            data_conclusao
        )

    campos.append(
        "data_atualizacao = ?"
    )

    valores.append(
        agora_iso()
    )

    valores.append(
        publicacao_id
    )

    query = f"""
        UPDATE publicacoes
        SET {", ".join(campos)}
        WHERE id = ?;
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            query,
            valores,
        )

        conexao.commit()

    finally:
        conexao.close()


def remover_publicacao(
    publicacao_id,
):
    """
    Remove uma publicação.

    As tabelas relacionadas
    serão removidas automaticamente
    por ON DELETE CASCADE.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            DELETE FROM publicacoes
            WHERE id = ?;
            """,
            (
                publicacao_id,
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


# ============================================================
# FILA DE PUBLICAÇÃO
# ============================================================


def adicionar_na_fila(
    publicacao_id,
    prioridade=100,
    max_tentativas=3,
    agendado_para=None,
    status="AGUARDANDO",
):
    """
    Adiciona uma publicação à fila.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            INSERT INTO fila_publicacao (
                publicacao_id,
                prioridade,
                status,
                tentativas,
                max_tentativas,
                agendado_para,
                data_criacao,
                data_atualizacao
            )
            VALUES (?, ?, ?, 0, ?, ?, ?, ?)

            ON CONFLICT(publicacao_id)
            DO UPDATE SET
                prioridade = excluded.prioridade,
                status = excluded.status,
                max_tentativas = excluded.max_tentativas,
                agendado_para = excluded.agendado_para,
                data_atualizacao = excluded.data_atualizacao;
            """,
            (
                publicacao_id,
                prioridade,
                status,
                max_tentativas,
                agendado_para,
                agora_iso(),
                agora_iso(),
            ),
        )

        conexao.commit()

        return cursor.lastrowid

    finally:
        conexao.close()


def obter_item_fila(
    publicacao_id,
):
    """
    Retorna o item da fila
    de uma publicação.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM fila_publicacao
            WHERE publicacao_id = ?;
            """,
            (
                publicacao_id,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()


def listar_fila(
    status=None,
):
    """
    Lista itens da fila.

    A menor prioridade numérica
    é processada primeiro.
    """

    conexao = conectar_banco()

    try:
        query = """
            SELECT
                fila_publicacao.*,
                publicacoes.conteudo_id,
                publicacoes.plataforma,
                publicacoes.canal_id
            FROM fila_publicacao
            INNER JOIN publicacoes
                ON publicacoes.id =
                   fila_publicacao.publicacao_id
            WHERE 1 = 1
        """

        parametros = []

        if status is not None:
            query += """
                AND fila_publicacao.status = ?
            """

            parametros.append(
                status
            )

        query += """
            ORDER BY
                fila_publicacao.prioridade ASC,
                fila_publicacao.data_criacao ASC;
        """

        cursor = conexao.execute(
            query,
            parametros,
        )

        return [
            dict(linha)
            for linha in cursor.fetchall()
        ]

    finally:
        conexao.close()


def atualizar_item_fila(
    publicacao_id,
    status=None,
    tentativas=None,
    ultimo_erro=None,
    iniciado_em=None,
    finalizado_em=None,
):
    """
    Atualiza um item da fila.
    """

    campos = []
    valores = []

    if status is not None:
        campos.append(
            "status = ?"
        )

        valores.append(
            status
        )

    if tentativas is not None:
        campos.append(
            "tentativas = ?"
        )

        valores.append(
            tentativas
        )

    if ultimo_erro is not None:
        campos.append(
            "ultimo_erro = ?"
        )

        valores.append(
            ultimo_erro
        )

    if iniciado_em is not None:
        campos.append(
            "iniciado_em = ?"
        )

        valores.append(
            iniciado_em
        )

    if finalizado_em is not None:
        campos.append(
            "finalizado_em = ?"
        )

        valores.append(
            finalizado_em
        )

    campos.append(
        "data_atualizacao = ?"
    )

    valores.append(
        agora_iso()
    )

    valores.append(
        publicacao_id
    )

    query = f"""
        UPDATE fila_publicacao
        SET {", ".join(campos)}
        WHERE publicacao_id = ?;
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            query,
            valores,
        )

        conexao.commit()

    finally:
        conexao.close()


def incrementar_tentativa_fila(
    publicacao_id,
):
    """
    Incrementa o número de tentativas
    de processamento da publicação.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            UPDATE fila_publicacao
            SET
                tentativas = tentativas + 1,
                data_atualizacao = ?
            WHERE publicacao_id = ?;
            """,
            (
                agora_iso(),
                publicacao_id,
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


# ============================================================
# ETAPAS DA PUBLICAÇÃO
# ============================================================


def salvar_etapa(
    publicacao_id,
    etapa,
    status="AGUARDANDO",
    obrigatoria=True,
):
    """
    Cria ou atualiza uma etapa
    da publicação.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            INSERT INTO etapas_publicacao (
                publicacao_id,
                etapa,
                status,
                obrigatoria,
                tentativas,
                data_atualizacao
            )
            VALUES (?, ?, ?, ?, 0, ?)

            ON CONFLICT(
                publicacao_id,
                etapa
            )
            DO UPDATE SET
                status = excluded.status,
                obrigatoria = excluded.obrigatoria,
                data_atualizacao =
                    excluded.data_atualizacao;
            """,
            (
                publicacao_id,
                etapa,
                status,
                1 if obrigatoria else 0,
                agora_iso(),
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


def obter_etapa(
    publicacao_id,
    etapa,
):
    """
    Retorna uma etapa específica.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM etapas_publicacao
            WHERE publicacao_id = ?
              AND etapa = ?;
            """,
            (
                publicacao_id,
                etapa,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()


def listar_etapas(
    publicacao_id,
):
    """
    Lista todas as etapas
    de uma publicação.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM etapas_publicacao
            WHERE publicacao_id = ?
            ORDER BY id;
            """,
            (
                publicacao_id,
            ),
        )

        return [
            dict(linha)
            for linha in cursor.fetchall()
        ]

    finally:
        conexao.close()


def atualizar_etapa(
    publicacao_id,
    etapa,
    status=None,
    tentativas=None,
    ultimo_erro=None,
    data_inicio=None,
    data_conclusao=None,
):
    """
    Atualiza o estado de uma etapa.
    """

    campos = []
    valores = []

    if status is not None:
        campos.append(
            "status = ?"
        )

        valores.append(
            status
        )

    if tentativas is not None:
        campos.append(
            "tentativas = ?"
        )

        valores.append(
            tentativas
        )

    if ultimo_erro is not None:
        campos.append(
            "ultimo_erro = ?"
        )

        valores.append(
            ultimo_erro
        )

    if data_inicio is not None:
        campos.append(
            "data_inicio = ?"
        )

        valores.append(
            data_inicio
        )

    if data_conclusao is not None:
        campos.append(
            "data_conclusao = ?"
        )

        valores.append(
            data_conclusao
        )

    campos.append(
        "data_atualizacao = ?"
    )

    valores.append(
        agora_iso()
    )

    valores.extend(
        [
            publicacao_id,
            etapa,
        ]
    )

    query = f"""
        UPDATE etapas_publicacao
        SET {", ".join(campos)}
        WHERE publicacao_id = ?
          AND etapa = ?;
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            query,
            valores,
        )

        conexao.commit()

    finally:
        conexao.close()


def incrementar_tentativa_etapa(
    publicacao_id,
    etapa,
):
    """
    Incrementa as tentativas
    de uma etapa.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            UPDATE etapas_publicacao
            SET
                tentativas = tentativas + 1,
                data_atualizacao = ?
            WHERE publicacao_id = ?
              AND etapa = ?;
            """,
            (
                agora_iso(),
                publicacao_id,
                etapa,
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


# ============================================================
# HISTÓRICO
# ============================================================


def registrar_historico(
    publicacao_id,
    etapa=None,
    status=None,
    mensagem=None,
    detalhes=None,
):
    """
    Registra um evento no histórico
    da publicação.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            INSERT INTO historico_publicacao (
                publicacao_id,
                etapa,
                status,
                mensagem,
                detalhes,
                data_evento
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                publicacao_id,
                etapa,
                status,
                mensagem,
                detalhes,
                agora_iso(),
            ),
        )

        conexao.commit()

        return cursor.lastrowid

    finally:
        conexao.close()


def listar_historico(
    publicacao_id,
):
    """
    Retorna o histórico completo
    de uma publicação.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM historico_publicacao
            WHERE publicacao_id = ?
            ORDER BY
                data_evento,
                id;
            """,
            (
                publicacao_id,
            ),
        )

        return [
            dict(linha)
            for linha in cursor.fetchall()
        ]

    finally:
        conexao.close()