"""Contratos da API (contracts/api.openapi.yaml) e modelos internos."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.guards import validar_pergunta

Dominio = Literal["financeiro", "informacoes_internas", "ouvidoria", "ambigua", "fora_de_escopo"]
Agente = Literal["orquestrador", "informacoes_internas", "ouvidoria", "financeiro"]
Status = Literal["ok", "nao_encontrado", "esclarecimento", "fora_de_escopo", "recusado", "erro"]
Modo = Literal["llm", "degradado"]


class AskRequest(BaseModel):
    pergunta: str

    @field_validator("pergunta")
    @classmethod
    def _validar(cls, v: str) -> str:
        return validar_pergunta(v)


class Fonte(BaseModel):
    tipo: Literal["arquivo", "protocolo", "lancamento", "consulta"]
    ref: str
    detalhe: str | None = None


class Classificacao(BaseModel):
    dominio: Dominio
    confianca: float = Field(ge=0, le=1)
    candidatos: list[Dominio] = []


class AskResponse(BaseModel):
    trace_id: str
    resposta: str
    dominio: Dominio
    agente: Agente
    confianca: float
    fontes: list[Fonte]
    status: Status
    modo: Modo
    latencia_ms: int


class Erro(BaseModel):
    trace_id: str
    detail: str
