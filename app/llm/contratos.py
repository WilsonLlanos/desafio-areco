"""Validação das saídas do LLM (contracts/llm-schemas.md).

A saída do modelo é dado não confiável. Campo desconhecido, valor fora do enum ou formato inválido
vira parâmetro ausente; o agente então pede esclarecimento. Classificação inválida vira baixa
confiança (→ esclarecimento).
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.api.schemas import Classificacao, Dominio
from app.queries.financeiro import ParamsFinanceiro
from app.queries.ouvidoria import PROTOCOLO_RE

DominioAgente = Literal["financeiro", "informacoes_internas", "ouvidoria"]


class SaidaClassificacao(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominio: Dominio
    confianca: float = Field(ge=0, le=1)
    candidatos: list[DominioAgente] = []


class ParamsOuvidoria(BaseModel):
    """Os enums (status, categoria, prioridade, canal) são conferidos pelo agente contra a referência,
    que responde com a lista de valores válidos."""
    model_config = ConfigDict(extra="forbid")

    consulta: Literal["buscar_protocolo", "contar", "listar", "referencia"] | None = None
    protocolo: str | None = Field(default=None, pattern=PROTOCOLO_RE.pattern)
    status: str | None = None
    categoria: str | None = None
    prioridade: str | None = None
    canal: str | None = None
    data_de: date | None = None
    data_ate: date | None = None  # exclusivo
    referencia_tipo: Literal["status", "categoria", "prioridade", "canal"] | None = None


class RespostaInternas(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resposta: str = Field(min_length=1, max_length=2000)
    fontes_usadas: list[str] = Field(min_length=1)


MODELOS_PARAMS = {"financeiro": ParamsFinanceiro, "ouvidoria": ParamsOuvidoria}
CLASSIFICACAO_INVALIDA = Classificacao(dominio="ambigua", confianca=0.0)


def validar_classificacao(dados) -> Classificacao:
    try:
        s = SaidaClassificacao.model_validate(dados)
    except ValidationError:
        return CLASSIFICACAO_INVALIDA
    return Classificacao(dominio=s.dominio, confianca=s.confianca, candidatos=s.candidatos)


def validar_params(dominio: str, dados) -> dict:
    """Mantém só os campos válidos; o que for inválido some (parâmetro ausente)."""
    modelo = MODELOS_PARAMS.get(dominio)
    if modelo is None or not isinstance(dados, dict):
        return {}
    dados = {k: v for k, v in dados.items() if k in modelo.model_fields and v is not None}
    if isinstance(dados.get("protocolo"), str):
        dados["protocolo"] = dados["protocolo"].strip().upper()
    while True:
        try:
            return modelo.model_validate(dados).model_dump(mode="json", exclude_none=True)
        except ValidationError as e:
            ruins = {err["loc"][0] for err in e.errors() if err["loc"]}
            if not ruins & dados.keys():
                return {}
            dados = {k: v for k, v in dados.items() if k not in ruins}


def validar_resposta(dados, fontes_permitidas: set[str]) -> RespostaInternas | None:
    """None se a saída for inválida ou citar fonte fora dos trechos recuperados."""
    try:
        r = RespostaInternas.model_validate(dados)
    except ValidationError:
        return None
    return r if set(r.fontes_usadas) <= fontes_permitidas else None
