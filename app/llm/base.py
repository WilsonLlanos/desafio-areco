"""Interface do LLM. Implementações: RulesLLM (sem chave), GeminiLLM (Fase 4) e FakeLLM (testes)."""
from typing import Protocol

from app.api.schemas import Classificacao


class LLMClient(Protocol):
    modo: str  # "llm" | "degradado"

    def classify(self, pergunta: str) -> Classificacao: ...

    def extract_params(self, dominio: str, pergunta: str) -> dict: ...

    def answer(self, pergunta: str, trechos: list[dict]) -> dict: ...


class FakeLLM:
    """LLM falso para testes: respostas roteirizadas, sem rede."""

    modo = "llm"

    def __init__(self, classificacao: Classificacao | None = None, params: dict | None = None):
        self.classificacao = classificacao
        self.params = params or {}
        self.chamadas: list[str] = []

    def classify(self, pergunta: str) -> Classificacao:
        self.chamadas.append("classify")
        if self.classificacao is None:
            return Classificacao(dominio="fora_de_escopo", confianca=0.9)
        return self.classificacao

    def extract_params(self, dominio: str, pergunta: str) -> dict:
        self.chamadas.append("extract_params")
        return dict(self.params)

    def answer(self, pergunta: str, trechos: list[dict]) -> dict:
        self.chamadas.append("answer")
        return {"resposta": "", "fontes_usadas": []}
