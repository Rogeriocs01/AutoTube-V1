import json
import hmac
from datetime import datetime
from uuid import uuid4

from core.database import conectar_banco
from core.snapshot_publicacao import calcular_fingerprint_snapshot


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


ETAPAS_YOUTUBE = (
    ("PREPARACAO", True),
    ("UPLOAD", True),
    ("PLAYLIST", False),
    ("THUMBNAIL", False),
    ("DRIVE", False),
    ("FINALIZACAO", True),
)


STATUS_BLOQUEANTES = {
    "AGUARDANDO",
    "PROCESSANDO",
    "PARCIAL",
    "CONCLUIDO",
    "RECONCILIACAO",
}


class ConflitoIdempotenciaError(RuntimeError):
    """Indica reutilização da chave com outra identidade de solicitação."""

    codigo = "idempotency_conflict"

    def __init__(self):
        super().__init__(
            "idempotency_conflict: chave já utilizada com outros parâmetros"
        )


class SnapshotDesatualizadoError(RuntimeError):
    """Indica divergência entre a prévia confirmada e os dados atuais."""

    codigo = "snapshot_stale"

    def __init__(self):
        super().__init__(
            "snapshot_stale: os dados da publicação foram alterados"
        )


def publicacao_bloqueia_nova_solicitacao(publicacao):
    """Aplica a regra comum de duplicidade sem alterar persistência."""

    dados = dict(publicacao)
    status = str(dados.get("status") or "").upper()
    external_id = str(dados.get("external_id") or "").strip()
    return status in STATUS_BLOQUEANTES or bool(external_id)


# ============================================================
# PUBLICAÇÕES
# ============================================================


def serializar_contrato_idempotente(valor):
    return json.dumps(
        valor,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def obter_resultado_solicitacao_idempotente(
    chave_idempotencia,
    identidade_solicitacao,
):
    """Recupera resposta persistida sem repetir a criação."""

    identidade_serializada = serializar_contrato_idempotente(
        identidade_solicitacao
    )
    conexao = conectar_banco()
    try:
        registro = conexao.execute(
            """
            SELECT identidade_solicitacao, resultado_criacao
            FROM idempotencia_solicitacao_publicacao
            WHERE chave = ?;
            """,
            (chave_idempotencia,),
        ).fetchone()
        if registro is None:
            return None
        if registro["identidade_solicitacao"] != identidade_serializada:
            raise ConflitoIdempotenciaError()
        return json.loads(registro["resultado_criacao"])
    finally:
        conexao.close()


def criar_solicitacao_atomica(
    conteudo_id,
    plataforma,
    canal_id=None,
    privacidade=None,
    prioridade=100,
    max_tentativas=3,
    agendado_para=None,
    publicacao_id=None,
    chave_idempotencia=None,
    identidade_solicitacao=None,
    resultado_criacao=None,
    snapshot_esperado=None,
):
    """Cria publicação, fila, etapas e histórico em uma transação."""

    publicacao_id = publicacao_id or gerar_id_publicacao()
    agora = agora_iso()
    identidade_serializada = None
    resultado_serializado = None
    if chave_idempotencia is not None:
        if not isinstance(identidade_solicitacao, dict):
            raise ValueError("identidade_solicitacao é obrigatória")
        if not isinstance(resultado_criacao, dict):
            raise ValueError("resultado_criacao é obrigatório")
        identidade_serializada = serializar_contrato_idempotente(
            identidade_solicitacao
        )
        resultado_persistido = dict(resultado_criacao)
        resultado_persistido["publicacao_id"] = publicacao_id
        resultado_serializado = serializar_contrato_idempotente(
            resultado_persistido
        )
    conexao = conectar_banco()

    try:
        conexao.execute("BEGIN IMMEDIATE;")
        if chave_idempotencia is not None:
            registro_idempotente = conexao.execute(
                """
                SELECT identidade_solicitacao, resultado_criacao
                FROM idempotencia_solicitacao_publicacao
                WHERE chave = ?;
                """,
                (chave_idempotencia,),
            ).fetchone()
            if registro_idempotente is not None:
                if (
                    registro_idempotente["identidade_solicitacao"]
                    != identidade_serializada
                ):
                    raise ConflitoIdempotenciaError()
                conexao.commit()
                return (
                    json.loads(registro_idempotente["resultado_criacao"]),
                    True,
                )

        if snapshot_esperado is not None:
            conteudo_atual = conexao.execute(
                "SELECT * FROM conteudos WHERE id = ?;",
                (conteudo_id,),
            ).fetchone()
            metadados_atuais = conexao.execute(
                "SELECT * FROM metadados WHERE conteudo_id = ?;",
                (conteudo_id,),
            ).fetchone()
            if conteudo_atual is None or metadados_atuais is None:
                raise SnapshotDesatualizadoError()
            snapshot_atual = calcular_fingerprint_snapshot(
                dict(conteudo_atual),
                dict(metadados_atuais),
                {
                    "conteudo_id": conteudo_id,
                    "privacidade": privacidade,
                    "canal_id": canal_id,
                    "prioridade": prioridade,
                    "plataforma": plataforma,
                    "agendado_para": agendado_para,
                },
            )
            if not hmac.compare_digest(snapshot_atual, snapshot_esperado):
                raise SnapshotDesatualizadoError()

        cursor = conexao.execute(
            """
            SELECT id, status, external_id
            FROM publicacoes
            WHERE conteudo_id = ?
              AND plataforma = ?
            ORDER BY data_criacao;
            """,
            (conteudo_id, plataforma),
        )

        for existente in cursor.fetchall():
            if publicacao_bloqueia_nova_solicitacao(existente):
                raise RuntimeError(
                    "Conteúdo já possui publicação bloqueante "
                    "para esta plataforma. "
                    f"publicacao_id={existente['id']} | "
                    f"status={existente['status']}"
                )

        conexao.execute(
            """
            INSERT INTO publicacoes (
                id, conteudo_id, plataforma, canal_id, privacidade,
                status, data_criacao, data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, 'AGUARDANDO', ?, ?);
            """,
            (
                publicacao_id,
                conteudo_id,
                plataforma,
                canal_id,
                privacidade,
                agora,
                agora,
            ),
        )
        conexao.execute(
            """
            INSERT INTO fila_publicacao (
                publicacao_id, prioridade, status, tentativas,
                max_tentativas, agendado_para, data_criacao,
                data_atualizacao
            )
            VALUES (?, ?, 'AGUARDANDO', 0, ?, ?, ?, ?);
            """,
            (
                publicacao_id,
                prioridade,
                max_tentativas,
                agendado_para,
                agora,
                agora,
            ),
        )

        for etapa, obrigatoria in ETAPAS_YOUTUBE:
            conexao.execute(
                """
                INSERT INTO etapas_publicacao (
                    publicacao_id, etapa, status, obrigatoria,
                    tentativas, data_atualizacao
                )
                VALUES (?, ?, 'AGUARDANDO', ?, 0, ?);
                """,
                (
                    publicacao_id,
                    etapa,
                    1 if obrigatoria else 0,
                    agora,
                ),
            )

        conexao.execute(
            """
            INSERT INTO historico_publicacao (
                publicacao_id, etapa, status, mensagem, data_evento
            )
            VALUES (?, 'CRIACAO', 'AGUARDANDO', ?, ?);
            """,
            (
                publicacao_id,
                "Solicitação de publicação criada",
                agora,
            ),
        )
        if chave_idempotencia is not None:
            conexao.execute(
                """
                INSERT INTO idempotencia_solicitacao_publicacao (
                    chave, identidade_solicitacao,
                    resultado_criacao, publicacao_id,
                    data_criacao
                )
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    chave_idempotencia,
                    identidade_serializada,
                    resultado_serializado,
                    publicacao_id,
                    agora,
                ),
            )
        conexao.commit()
        if chave_idempotencia is not None:
            if resultado_serializado is None:
                raise RuntimeError("resultado idempotente não foi serializado")
            return (
                json.loads(resultado_serializado),
                False,
            )
        return publicacao_id
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def adquirir_execucao(publicacao_id):
    """Adquire atomicamente o direito exclusivo de executar um job."""

    agora = agora_iso()
    conexao = conectar_banco()

    try:
        conexao.execute("BEGIN IMMEDIATE;")
        cursor = conexao.execute(
            """
            SELECT
                publicacoes.conteudo_id,
                publicacoes.plataforma,
                publicacoes.status AS status_publicacao,
                publicacoes.external_id,
                fila_publicacao.status AS status_fila,
                fila_publicacao.tentativas,
                fila_publicacao.max_tentativas,
                fila_publicacao.agendado_para
            FROM publicacoes
            INNER JOIN fila_publicacao
                ON fila_publicacao.publicacao_id = publicacoes.id
            WHERE publicacoes.id = ?;
            """,
            (publicacao_id,),
        )
        estado = cursor.fetchone()

        if estado is None:
            raise ValueError(
                f"Publicação ou fila não encontrada: {publicacao_id}"
            )

        status_publicacao = str(estado["status_publicacao"] or "").upper()
        status_fila = str(estado["status_fila"] or "").upper()
        external_id = str(estado["external_id"] or "").strip()
        tentativas = estado["tentativas"] or 0
        max_tentativas = estado["max_tentativas"] or 0

        conflito = conexao.execute(
            """
            SELECT id, status, external_id
            FROM publicacoes
            WHERE conteudo_id = ?
              AND plataforma = ?
              AND id <> ?
              AND (
                    status IN (
                        'PROCESSANDO', 'PARCIAL', 'CONCLUIDO',
                        'RECONCILIACAO'
                    )
                    OR (external_id IS NOT NULL AND TRIM(external_id) <> '')
                  )
            LIMIT 1;
            """,
            (
                estado["conteudo_id"],
                estado["plataforma"],
                publicacao_id,
            ),
        ).fetchone()

        if conflito is not None:
            raise RuntimeError(
                "Execução bloqueada: outra publicação do mesmo conteúdo e "
                "plataforma já está processando ou possui upload realizado."
            )

        if external_id:
            raise RuntimeError(
                "Execução bloqueada: external_id indica upload já realizado."
            )
        if status_publicacao not in {"AGUARDANDO", "ERRO"}:
            raise RuntimeError(
                "Publicação não pode ser executada. "
                f"Status atual: {status_publicacao}"
            )
        if status_fila not in {"AGUARDANDO", "ERRO"}:
            raise RuntimeError(
                "Item da fila não pode ser executado. "
                f"Status atual: {status_fila}"
            )
        if max_tentativas > 0 and tentativas >= max_tentativas:
            raise RuntimeError(
                "Limite máximo de tentativas atingido. "
                f"Tentativas: {tentativas}/{max_tentativas}"
            )

        agendado_para = estado["agendado_para"]
        if agendado_para:
            try:
                agendamento = datetime.fromisoformat(agendado_para)
                referencia = datetime.now(tz=agendamento.tzinfo)
            except (TypeError, ValueError) as erro:
                raise RuntimeError(
                    "Agendamento inválido; execução bloqueada."
                ) from erro
            if agendamento > referencia:
                raise RuntimeError(
                    "Execução antecipada bloqueada: trabalho agendado para o futuro."
                )

        cursor_publicacao = conexao.execute(
            """
            UPDATE publicacoes
            SET status = 'PROCESSANDO', data_inicio = ?,
                data_atualizacao = ?
            WHERE id = ?
              AND status IN ('AGUARDANDO', 'ERRO')
              AND (external_id IS NULL OR TRIM(external_id) = '');
            """,
            (agora, agora, publicacao_id),
        )
        cursor_fila = conexao.execute(
            """
            UPDATE fila_publicacao
            SET status = 'PROCESSANDO', tentativas = tentativas + 1,
                iniciado_em = ?, ultimo_erro = '', data_atualizacao = ?
            WHERE publicacao_id = ?
              AND status IN ('AGUARDANDO', 'ERRO');
            """,
            (agora, agora, publicacao_id),
        )

        if cursor_publicacao.rowcount != 1 or cursor_fila.rowcount != 1:
            raise RuntimeError(
                "Execução não adquirida; o job foi assumido por outro processo."
            )

        conexao.execute(
            """
            INSERT INTO historico_publicacao (
                publicacao_id, etapa, status, mensagem, data_evento
            )
            VALUES (?, 'EXECUCAO', 'PROCESSANDO', ?, ?);
            """,
            (
                publicacao_id,
                "Processamento da publicação iniciado",
                agora,
            ),
        )
        conexao.commit()
        return {
            "status_publicacao": "PROCESSANDO",
            "status_fila": "PROCESSANDO",
            "tentativas": tentativas + 1,
            "max_tentativas": max_tentativas,
        }
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


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


def registrar_evento_etapa_atomico(
    publicacao_id,
    etapa,
    status,
    mensagem=None,
    detalhes=None,
    external_id=None,
):
    """Atualiza etapa, resultado do upload e histórico atomicamente."""

    agora = agora_iso()
    conexao = conectar_banco()

    try:
        conexao.execute("BEGIN IMMEDIATE;")

        if status == "PROCESSANDO":
            cursor = conexao.execute(
                """
                UPDATE etapas_publicacao
                SET status = 'PROCESSANDO', tentativas = tentativas + 1,
                    ultimo_erro = '', data_inicio = ?, data_atualizacao = ?
                WHERE publicacao_id = ? AND etapa = ?;
                """,
                (agora, agora, publicacao_id, etapa),
            )
        elif status in ("CONCLUIDO", "IGNORADO"):
            cursor = conexao.execute(
                """
                UPDATE etapas_publicacao
                SET status = ?, ultimo_erro = '', data_conclusao = ?,
                    data_atualizacao = ?
                WHERE publicacao_id = ? AND etapa = ?;
                """,
                (status, agora, agora, publicacao_id, etapa),
            )
        elif status == "ERRO":
            cursor = conexao.execute(
                """
                UPDATE etapas_publicacao
                SET status = 'ERRO', ultimo_erro = ?, data_conclusao = ?,
                    data_atualizacao = ?
                WHERE publicacao_id = ? AND etapa = ?;
                """,
                (
                    mensagem or "Falha na etapa",
                    agora,
                    agora,
                    publicacao_id,
                    etapa,
                ),
            )
        else:
            cursor = conexao.execute(
                """
                UPDATE etapas_publicacao
                SET status = ?, data_atualizacao = ?
                WHERE publicacao_id = ? AND etapa = ?;
                """,
                (status, agora, publicacao_id, etapa),
            )

        if cursor.rowcount != 1:
            raise ValueError(
                f"Etapa não encontrada: {publicacao_id}/{etapa}"
            )

        if etapa == "UPLOAD" and status == "CONCLUIDO" and external_id:
            conexao.execute(
                """
                UPDATE publicacoes
                SET external_id = ?, data_atualizacao = ?
                WHERE id = ?;
                """,
                (external_id, agora, publicacao_id),
            )

        conexao.execute(
            """
            INSERT INTO historico_publicacao (
                publicacao_id, etapa, status, mensagem, detalhes, data_evento
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                publicacao_id,
                etapa,
                status,
                mensagem,
                detalhes,
                agora,
            ),
        )
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def finalizar_execucao_atomica(
    publicacao_id,
    status,
    etapa,
    mensagem,
    external_id=None,
    ultimo_erro=None,
    detalhes=None,
):
    """Finaliza publicação, fila e histórico em uma transação."""

    agora = agora_iso()
    conexao = conectar_banco()

    try:
        conexao.execute("BEGIN IMMEDIATE;")
        if external_id:
            conexao.execute(
                """
                UPDATE publicacoes
                SET status = ?, external_id = ?,
                    data_conclusao = CASE WHEN ? = 'CONCLUIDO' THEN ?
                                         ELSE data_conclusao END,
                    data_atualizacao = ?
                WHERE id = ?;
                """,
                (status, external_id, status, agora, agora, publicacao_id),
            )
        else:
            conexao.execute(
                """
                UPDATE publicacoes
                SET status = ?,
                    data_conclusao = CASE WHEN ? = 'CONCLUIDO' THEN ?
                                         ELSE data_conclusao END,
                    data_atualizacao = ?
                WHERE id = ?;
                """,
                (status, status, agora, agora, publicacao_id),
            )

        conexao.execute(
            """
            UPDATE fila_publicacao
            SET status = ?, ultimo_erro = ?,
                finalizado_em = CASE WHEN ? = 'CONCLUIDO' THEN ?
                                     ELSE finalizado_em END,
                data_atualizacao = ?
            WHERE publicacao_id = ?;
            """,
            (
                status,
                ultimo_erro or "",
                status,
                agora,
                agora,
                publicacao_id,
            ),
        )
        conexao.execute(
            """
            INSERT INTO historico_publicacao (
                publicacao_id, etapa, status, mensagem, detalhes, data_evento
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                publicacao_id,
                etapa,
                status,
                mensagem,
                detalhes,
                agora,
            ),
        )
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
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