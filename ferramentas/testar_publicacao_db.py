import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


from core.repositorio import (
    obter_conteudo,
    obter_metadados,
)

from core.repositorio_publicacao import (
    listar_etapas,
    obter_item_fila,
    obter_publicacao,
)


def status_ok(condicao):
    if condicao:
        return "OK"

    return "FALHOU"


def testar_publicacao(publicacao_id):
    print()
    print("========================================")
    print("       PRÉ-VOO DE PUBLICAÇÃO")
    print("========================================")
    print()

    publicacao = obter_publicacao(
        publicacao_id
    )

    if publicacao is None:
        print(
            "Publicação   : NÃO ENCONTRADA"
        )
        print()
        print(
            "Resultado    : NÃO ESTÁ PRONTO"
        )
        return False

    conteudo_id = publicacao.get(
        "conteudo_id"
    )

    conteudo = obter_conteudo(
        conteudo_id
    )

    metadados = obter_metadados(
        conteudo_id
    )

    fila = obter_item_fila(
        publicacao_id
    )

    etapas = listar_etapas(
        publicacao_id
    )

    conteudo_ok = (
        conteudo is not None
    )

    metadados_ok = (
        metadados is not None
        and bool(
            str(
                metadados.get(
                    "titulo",
                    "",
                )
            ).strip()
        )
    )

    arquivo_ok = (
        conteudo_ok
        and bool(
            str(
                conteudo.get(
                    "nome_arquivo",
                    "",
                )
            ).strip()
        )
    )

    drive_ok = (
        conteudo_ok
        and bool(
            str(
                conteudo.get(
                    "drive_file_id",
                    "",
                )
            ).strip()
        )
    )

    publicacao_ok = (
        publicacao.get(
            "status"
        )
        == "AGUARDANDO"
    )

    fila_ok = (
        fila is not None
        and fila.get(
            "status"
        )
        == "AGUARDANDO"
    )

    tentativas = 0

    if fila is not None:
        tentativas = (
            fila.get(
                "tentativas"
            )
            or 0
        )

    tentativas_ok = (
        tentativas == 0
    )

    etapas_ok = (
        len(etapas) == 6
    )

    etapas_aguardando = all(
        etapa.get(
            "status"
        )
        == "AGUARDANDO"
        for etapa in etapas
    )

    print(
        f"Publicação ID : {publicacao_id}"
    )

    print(
        f"Conteúdo ID   : {conteudo_id}"
    )

    print()

    print(
        f"Conteúdo      : "
        f"{status_ok(conteudo_ok)}"
    )

    print(
        f"Metadados     : "
        f"{status_ok(metadados_ok)}"
    )

    print(
        f"Arquivo       : "
        f"{status_ok(arquivo_ok)}"
    )

    print(
        f"Drive ID      : "
        f"{status_ok(drive_ok)}"
    )

    print(
        f"Publicação    : "
        f"{publicacao.get('status')}"
    )

    if fila is not None:
        print(
            f"Fila          : "
            f"{fila.get('status')}"
        )
    else:
        print(
            "Fila          : NÃO ENCONTRADA"
        )

    print(
        f"Tentativas    : {tentativas}"
    )

    print(
        f"Etapas        : {len(etapas)}"
    )

    print()

    if etapas:
        print("ETAPAS:")

        for etapa in etapas:
            nome = etapa.get(
                "etapa"
            )

            status = etapa.get(
                "status"
            )

            obrigatoria = etapa.get(
                "obrigatoria"
            )

            if obrigatoria:
                tipo = "obrigatória"
            else:
                tipo = "opcional"

            print(
                f"  - {nome}: "
                f"{status} "
                f"({tipo})"
            )

        print()

    pronto = all(
        [
            conteudo_ok,
            metadados_ok,
            arquivo_ok,
            drive_ok,
            publicacao_ok,
            fila_ok,
            tentativas_ok,
            etapas_ok,
            etapas_aguardando,
        ]
    )

    print("----------------------------------------")

    if pronto:
        print(
            "Resultado     : "
            "PRONTO PARA EXECUÇÃO"
        )
    else:
        print(
            "Resultado     : "
            "NÃO ESTÁ PRONTO"
        )

    print("----------------------------------------")
    print()

    print(
        "Este teste NÃO executou upload, "
        "download ou alteração de estado."
    )

    print()

    return pronto


def main():
    if len(sys.argv) < 2:
        print()
        print(
            "Uso:"
        )

        print(
            "python "
            "ferramentas/testar_publicacao_db.py "
            "<publicacao_id>"
        )

        print()

        return

    publicacao_id = (
        sys.argv[1].strip()
    )

    testar_publicacao(
        publicacao_id
    )


if __name__ == "__main__":
    main()