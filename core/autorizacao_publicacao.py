"""Contrato verificável de autorização supervisionada."""

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4


class ErroAutorizacaoSupervisionada(RuntimeError):
    """Erro controlado do contrato de autorização."""

    def __init__(self, codigo, mensagem):
        self.codigo = codigo
        super().__init__(f"{codigo}: {mensagem}")


@dataclass(frozen=True)
class ContextoOperadorConfiavel:
    emissor_id: str
    autorizador_id: str
    assinatura: str


@dataclass(frozen=True)
class AutorizacaoSupervisionada:
    autorizacao_id: str
    emissor_id: str
    autorizador_id: str
    confirmado_em: str
    expira_em: str
    conteudo_id: str
    canal_id: str | None
    plataforma: str
    privacidade: str
    prioridade: int
    agendado_para: str | None
    snapshot_fingerprint: str
    assinatura: str

    def dados_assinados(self):
        dados = asdict(self)
        dados.pop("assinatura")
        return dados

    def dados_auditoria(self):
        return self.dados_assinados()


class EmissorAutorizacaoSupervisionada:
    """Emissor local que atua como capacidade confiável configurada no serviço."""

    def __init__(
        self,
        emissor_id,
        relogio=None,
        validade_maxima_segundos=300,
    ):
        if not isinstance(emissor_id, str) or not emissor_id.strip():
            raise ValueError("emissor_id inválido")
        if validade_maxima_segundos <= 0:
            raise ValueError("validade_maxima_segundos deve ser positivo")
        self.emissor_id = emissor_id
        self._relogio = relogio or (lambda: datetime.now(timezone.utc))
        self._validade_maxima_segundos = validade_maxima_segundos
        self._segredo = secrets.token_bytes(32)

    def _agora(self):
        agora = self._relogio()
        if agora.tzinfo is None or agora.utcoffset() is None:
            raise ValueError("o relógio deve retornar data com fuso horário")
        return agora.astimezone(timezone.utc)

    def _assinar(self, dominio, dados):
        serializado = json.dumps(
            {"dominio": dominio, "dados": dados},
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hmac.new(
            self._segredo,
            serializado,
            hashlib.sha256,
        ).hexdigest()

    def criar_contexto_operador(self, autorizador_id):
        """Cria uma capacidade que deve ficar restrita ao adaptador autenticado."""

        if not isinstance(autorizador_id, str) or not autorizador_id.strip():
            raise ValueError("autorizador_id inválido")
        dados = {
            "emissor_id": self.emissor_id,
            "autorizador_id": autorizador_id,
        }
        return ContextoOperadorConfiavel(
            **dados,
            assinatura=self._assinar("contexto_operador", dados),
        )

    def _validar_contexto_operador(self, contexto):
        if not isinstance(contexto, ContextoOperadorConfiavel):
            raise ErroAutorizacaoSupervisionada(
                "authorization_invalid",
                "contexto do operador inválido",
            )
        dados = {
            "emissor_id": contexto.emissor_id,
            "autorizador_id": contexto.autorizador_id,
        }
        assinatura_esperada = self._assinar("contexto_operador", dados)
        if (
            contexto.emissor_id != self.emissor_id
            or not hmac.compare_digest(
                contexto.assinatura,
                assinatura_esperada,
            )
        ):
            raise ErroAutorizacaoSupervisionada(
                "authorization_invalid",
                "contexto do operador inválido",
            )

    def emitir(
        self,
        contexto_operador,
        conteudo_id,
        canal_id,
        plataforma,
        privacidade,
        prioridade,
        agendado_para,
        snapshot_fingerprint,
        validade_segundos=60,
    ):
        """Emite autorização curta, assinada e vinculada aos dados confirmados."""

        self._validar_contexto_operador(contexto_operador)
        if (
            not isinstance(validade_segundos, int)
            or isinstance(validade_segundos, bool)
            or validade_segundos <= 0
            or validade_segundos > self._validade_maxima_segundos
        ):
            raise ValueError("validade_segundos fora do intervalo permitido")
        agora = self._agora()
        dados = {
            "autorizacao_id": "auth_" + uuid4().hex,
            "emissor_id": self.emissor_id,
            "autorizador_id": contexto_operador.autorizador_id,
            "confirmado_em": agora.isoformat(),
            "expira_em": (
                agora + timedelta(seconds=validade_segundos)
            ).isoformat(),
            "conteudo_id": conteudo_id,
            "canal_id": canal_id,
            "plataforma": plataforma,
            "privacidade": privacidade,
            "prioridade": prioridade,
            "agendado_para": agendado_para,
            "snapshot_fingerprint": snapshot_fingerprint,
        }
        return AutorizacaoSupervisionada(
            **dados,
            assinatura=self._assinar("autorizacao_publicacao", dados),
        )

    def validar_assinatura(self, autorizacao):
        if autorizacao is None:
            raise ErroAutorizacaoSupervisionada(
                "authorization_required",
                "autorização supervisionada obrigatória",
            )
        if not isinstance(autorizacao, AutorizacaoSupervisionada):
            raise ErroAutorizacaoSupervisionada(
                "authorization_invalid",
                "contrato de autorização inválido",
            )
        dados = autorizacao.dados_assinados()
        assinatura_esperada = self._assinar(
            "autorizacao_publicacao",
            dados,
        )
        if (
            autorizacao.emissor_id != self.emissor_id
            or not hmac.compare_digest(
                autorizacao.assinatura,
                assinatura_esperada,
            )
        ):
            raise ErroAutorizacaoSupervisionada(
                "authorization_invalid",
                "autorização não foi emitida pelo componente confiável",
            )

    def validar_confirmacao(
        self,
        autorizacao,
        parametros,
        snapshot_esperado,
        verificar_expiracao=True,
    ):
        self.validar_assinatura(autorizacao)
        esperado = {
            "conteudo_id": parametros["conteudo_id"],
            "canal_id": parametros["canal_id"],
            "plataforma": parametros["plataforma"],
            "privacidade": parametros["privacidade"],
            "prioridade": parametros["prioridade"],
            "agendado_para": parametros["agendado_para"],
            "snapshot_fingerprint": snapshot_esperado,
        }
        confirmado = {
            campo: getattr(autorizacao, campo)
            for campo in esperado
        }
        if confirmado != esperado:
            raise ErroAutorizacaoSupervisionada(
                "authorization_mismatch",
                "autorização não corresponde aos parâmetros confirmados",
            )
        if verificar_expiracao:
            expira_em = datetime.fromisoformat(autorizacao.expira_em)
            if self._agora() >= expira_em.astimezone(timezone.utc):
                raise ErroAutorizacaoSupervisionada(
                    "authorization_expired",
                    "autorização expirada",
                )
