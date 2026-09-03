import sqlite3

from config import PASTA_AUTOTUBE_DATA


ARQUIVO_BANCO = (
    PASTA_AUTOTUBE_DATA
    / "autotube.db"
)


def conectar_banco():
    """
    Abre conexão com o banco SQLite
    do AutoTube.
    """

    PASTA_AUTOTUBE_DATA.mkdir(
        parents=True,
        exist_ok=True,
    )

    conexao = sqlite3.connect(
        ARQUIVO_BANCO
    )

    conexao.row_factory = (
        sqlite3.Row
    )

    conexao.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return conexao


def criar_schema():
    """
    Cria o schema do AutoTube V1.2.

    O banco existe paralelamente
    aos arquivos JSON durante
    a fase de migração.

    Cada conteúdo possui um ID global
    independente do ID legado usado
    atualmente pelo AutoTube.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projetos (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                slug TEXT,
                descricao TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conteudos (
                id TEXT PRIMARY KEY,
                projeto_id TEXT NOT NULL,
                id_legado TEXT,
                tipo TEXT,
                nome_arquivo TEXT,
                origem TEXT,
                conteudo_pai_id TEXT,
                drive_file_id TEXT,
                status TEXT NOT NULL DEFAULT 'PENDENTE',
                data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    projeto_id,
                    id_legado
                ),

                FOREIGN KEY (
                    projeto_id
                )
                REFERENCES projetos (
                    id
                ),

                FOREIGN KEY (
                    conteudo_pai_id
                )
                REFERENCES conteudos (
                    id
                )
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conteudo_id TEXT NOT NULL UNIQUE,
                titulo TEXT,
                descricao TEXT,
                hashtags TEXT,
                playlist_id TEXT,
                playlist_nome TEXT,
                idioma TEXT,
                categoria TEXT,
                data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    conteudo_id
                )
                REFERENCES conteudos (
                    id
                )
                ON DELETE CASCADE
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS publicacoes (
                id TEXT PRIMARY KEY,
                conteudo_id TEXT NOT NULL,
                plataforma TEXT NOT NULL,
                canal_id TEXT,
                privacidade TEXT,
                status TEXT NOT NULL DEFAULT 'AGUARDANDO',
                external_id TEXT,
                url TEXT,
                data_inicio TEXT,
                data_conclusao TEXT,
                data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    conteudo_id
                )
                REFERENCES conteudos (
                    id
                )
                ON DELETE CASCADE
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fila_publicacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacao_id TEXT NOT NULL UNIQUE,
                prioridade INTEGER NOT NULL DEFAULT 100,
                status TEXT NOT NULL DEFAULT 'AGUARDANDO',
                tentativas INTEGER NOT NULL DEFAULT 0,
                max_tentativas INTEGER NOT NULL DEFAULT 3,
                agendado_para TEXT,
                iniciado_em TEXT,
                finalizado_em TEXT,
                ultimo_erro TEXT,
                data_criacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    publicacao_id
                )
                REFERENCES publicacoes (
                    id
                )
                ON DELETE CASCADE
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS etapas_publicacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacao_id TEXT NOT NULL,
                etapa TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'AGUARDANDO',
                obrigatoria INTEGER NOT NULL DEFAULT 1,
                tentativas INTEGER NOT NULL DEFAULT 0,
                ultimo_erro TEXT,
                data_inicio TEXT,
                data_conclusao TEXT,
                data_atualizacao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    publicacao_id,
                    etapa
                ),

                FOREIGN KEY (
                    publicacao_id
                )
                REFERENCES publicacoes (
                    id
                )
                ON DELETE CASCADE
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS historico_publicacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publicacao_id TEXT NOT NULL,
                etapa TEXT,
                status TEXT,
                mensagem TEXT,
                detalhes TEXT,
                data_evento TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (
                    publicacao_id
                )
                REFERENCES publicacoes (
                    id
                )
                ON DELETE CASCADE
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_conteudos_projeto
            ON conteudos (
                projeto_id
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_conteudos_status
            ON conteudos (
                status
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_conteudos_projeto_legado
            ON conteudos (
                projeto_id,
                id_legado
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_publicacoes_conteudo
            ON publicacoes (
                conteudo_id
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_publicacoes_status
            ON publicacoes (
                status
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_fila_status_prioridade
            ON fila_publicacao (
                status,
                prioridade
            );
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_historico_publicacao
            ON historico_publicacao (
                publicacao_id,
                data_evento
            );
            """
        )

        conexao.commit()

    finally:
        conexao.close()


def listar_tabelas():
    """
    Retorna as tabelas existentes
    no banco.
    """

    conexao = conectar_banco()

    try:
        cursor = conexao.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name;
            """
        )

        return [
            linha["name"]
            for linha in cursor.fetchall()
        ]

    finally:
        conexao.close()