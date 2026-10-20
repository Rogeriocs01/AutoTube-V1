"""
Interface oficial de integração do AutoTube com o ecossistema.

Camada fina: não contém regras de negócio, não acessa SQLite
nem executa o pipeline diretamente. As operações são delegadas
ao serviço interno de publicação.
"""

from core.servico_publicacao_db import servico_publicacao_db


class InterfaceAutoTube:
    """Porta pública de integração do AutoTube."""

    def __init__(self, servico=None):
        self._servico = servico or servico_publicacao_db

    def solicitar_publicacao(
        self,
        conteudo_id,
        privacidade="private",
        canal_id=None,
        prioridade=100,
        plataforma="YOUTUBE",
        agendado_para=None,
        chave_idempotencia=None,
        snapshot_esperado=None,
    ):
        """Cria uma solicitação e a adiciona à fila. Não executa upload."""
        parametros = {
            "conteudo_id": conteudo_id,
            "privacidade": privacidade,
            "canal_id": canal_id,
            "prioridade": prioridade,
            "plataforma": plataforma,
            "agendado_para": agendado_para,
        }
        if chave_idempotencia is not None:
            parametros["chave_idempotencia"] = chave_idempotencia
        if snapshot_esperado is not None:
            parametros["snapshot_esperado"] = snapshot_esperado
        return self._servico.criar_solicitacao(**parametros)

    def previsualizar_publicacao(
        self,
        conteudo_id,
        privacidade="private",
        canal_id=None,
        prioridade=100,
        plataforma="YOUTUBE",
        agendado_para=None,
    ):
        """Avalia elegibilidade local sem criar ou executar publicação."""
        return self._servico.previsualizar_publicacao(
            conteudo_id=conteudo_id,
            privacidade=privacidade,
            canal_id=canal_id,
            prioridade=prioridade,
            plataforma=plataforma,
            agendado_para=agendado_para,
        )

    def solicitar_publicacao_supervisionada(
        self,
        autorizacao,
        conteudo_id,
        privacidade="private",
        canal_id=None,
        prioridade=100,
        plataforma="YOUTUBE",
        agendado_para=None,
        chave_idempotencia=None,
        snapshot_esperado=None,
    ):
        """Cria solicitação auditada; não autoriza execução ou upload."""

        return self._servico.criar_solicitacao_supervisionada(
            autorizacao=autorizacao,
            conteudo_id=conteudo_id,
            privacidade=privacidade,
            canal_id=canal_id,
            prioridade=prioridade,
            plataforma=plataforma,
            agendado_para=agendado_para,
            chave_idempotencia=chave_idempotencia,
            snapshot_esperado=snapshot_esperado,
        )

    def consultar_proximo_job(self):
        """Consulta o próximo job aguardando. Somente leitura."""
        return self._servico.consultar_proximo_job()

    def obter_job(self, job_id):
        """Consulta um job específico. Somente leitura."""
        return self._servico.obter_job(job_id)

    def executar_job(self, job_id):
        """
        Executa um job existente.

        ATENÇÃO: esta operação pode realizar uma publicação real.
        """
        return self._servico.executar_job(job_id)

    def obter_resultado(self, publicacao_id):
        """Consulta o estado e o resultado atual de uma publicação."""
        return self._servico.obter_resultado(publicacao_id)

    def listar_eventos(self, publicacao_id):
        """Consulta os eventos registrados para uma publicação."""
        return self._servico.listar_eventos(publicacao_id)


interface_autotube = InterfaceAutoTube()
