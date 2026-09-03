from datetime import datetime

from core.database import conectar_banco


def agora_iso():
    """
    Retorna data/hora atual em formato ISO.
    """

    return datetime.now().isoformat(
        timespec="seconds"
    )


def salvar_projeto(
    projeto_id,
    nome,
    slug=None,
    descricao=None,
    ativo=True,
):
    """
    Cria ou atualiza um projeto.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            INSERT INTO projetos (
                id,
                nome,
                slug,
                descricao,
                ativo,
                data_criacao,
                data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(id)
            DO UPDATE SET
                nome = excluded.nome,
                slug = excluded.slug,
                descricao = excluded.descricao,
                ativo = excluded.ativo,
                data_atualizacao = excluded.data_atualizacao;
            """,
            (
                projeto_id,
                nome,
                slug,
                descricao,
                1 if ativo else 0,
                agora_iso(),
                agora_iso(),
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


def obter_projeto(
    projeto_id,
):
    """
    Retorna um projeto pelo ID.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM projetos
            WHERE id = ?;
            """,
            (
                projeto_id,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()


def listar_projetos():
    """
    Retorna todos os projetos.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM projetos
            ORDER BY nome;
            """
        )

        return [
            dict(linha)
            for linha in cursor.fetchall()
        ]

    finally:
        conexao.close()


def salvar_conteudo(
    conteudo_id,
    projeto_id,
    id_legado=None,
    tipo=None,
    nome_arquivo=None,
    origem=None,
    conteudo_pai_id=None,
    drive_file_id=None,
    status="PENDENTE",
):
    """
    Cria ou atualiza um conteúdo.

    conteudo_id:
        ID global usado pelo novo modelo.

    id_legado:
        ID usado pelo AutoTube atual,
        como YT_0001.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            INSERT INTO conteudos (
                id,
                projeto_id,
                id_legado,
                tipo,
                nome_arquivo,
                origem,
                conteudo_pai_id,
                drive_file_id,
                status,
                data_criacao,
                data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(id)
            DO UPDATE SET
                projeto_id = excluded.projeto_id,
                id_legado = excluded.id_legado,
                tipo = excluded.tipo,
                nome_arquivo = excluded.nome_arquivo,
                origem = excluded.origem,
                conteudo_pai_id = excluded.conteudo_pai_id,
                drive_file_id = excluded.drive_file_id,
                status = excluded.status,
                data_atualizacao = excluded.data_atualizacao;
            """,
            (
                conteudo_id,
                projeto_id,
                id_legado,
                tipo,
                nome_arquivo,
                origem,
                conteudo_pai_id,
                drive_file_id,
                status,
                agora_iso(),
                agora_iso(),
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


def obter_conteudo(
    conteudo_id,
):
    """
    Retorna um conteúdo pelo ID global.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM conteudos
            WHERE id = ?;
            """,
            (
                conteudo_id,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()


def obter_conteudo_por_id_legado(
    projeto_id,
    id_legado,
):
    """
    Retorna um conteúdo usando o ID legado
    dentro de um projeto específico.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM conteudos
            WHERE projeto_id = ?
              AND id_legado = ?;
            """,
            (
                projeto_id,
                id_legado,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()


def listar_conteudos(
    projeto_id=None,
    status=None,
):
    """
    Lista conteúdos com filtros opcionais.
    """

    conexao = conectar_banco()

    try:
        query = """
            SELECT *
            FROM conteudos
            WHERE 1 = 1
        """

        parametros = []

        if projeto_id is not None:
            query += """
                AND projeto_id = ?
            """

            parametros.append(
                projeto_id
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


def salvar_metadados(
    conteudo_id,
    titulo=None,
    descricao=None,
    hashtags=None,
    playlist_id=None,
    playlist_nome=None,
    idioma=None,
    categoria=None,
):
    """
    Cria ou atualiza os metadados
    de um conteúdo.
    """

    conexao = conectar_banco()

    try:
        conexao.execute(
            """
            INSERT INTO metadados (
                conteudo_id,
                titulo,
                descricao,
                hashtags,
                playlist_id,
                playlist_nome,
                idioma,
                categoria,
                data_criacao,
                data_atualizacao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(conteudo_id)
            DO UPDATE SET
                titulo = excluded.titulo,
                descricao = excluded.descricao,
                hashtags = excluded.hashtags,
                playlist_id = excluded.playlist_id,
                playlist_nome = excluded.playlist_nome,
                idioma = excluded.idioma,
                categoria = excluded.categoria,
                data_atualizacao = excluded.data_atualizacao;
            """,
            (
                conteudo_id,
                titulo,
                descricao,
                hashtags,
                playlist_id,
                playlist_nome,
                idioma,
                categoria,
                agora_iso(),
                agora_iso(),
            ),
        )

        conexao.commit()

    finally:
        conexao.close()


def obter_metadados(
    conteudo_id,
):
    """
    Retorna os metadados de um conteúdo.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT *
            FROM metadados
            WHERE conteudo_id = ?;
            """,
            (
                conteudo_id,
            ),
        )

        linha = cursor.fetchone()

        if linha is None:
            return None

        return dict(linha)

    finally:
        conexao.close()