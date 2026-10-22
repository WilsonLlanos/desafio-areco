"""Interface do LLM. Implementações: RulesLLM (sem chave), GeminiLLM (Fase 4) e FakeLLM (testes)."""
from typing import Protocol

from app.api.schemas import Classificacao


class ErroLLM(RuntimeError):
    """Falha do provedor (rede, timeout, cota, resposta vazia). O orquestrador cai para as regras."""


class LLMClient(Protocol):
    modo: str  # "llm" | "degradado"

    def classify(self, pergunta: str) -> Classificacao: ...

    def extract_params(self, dominio: str, pergunta: str) -> dict: ...

    def answer(self, pergunta: str, trechos: list[dict]) -> dict: ...


class FakeLLM:
    """LLM falso para testes: respostas roteirizadas, sem rede. `falha` faz todas as chamadas falharem."""

    modo = "llm"

    def __init__(self, classificacao: Classificacao | None = None, params: dict | None = None,
                 resposta: dict | None = None, falha: Exception | None = None):
        self.classificacao = classificacao
        self.params = params or {}
        self.resposta = resposta
        self.falha = falha
        self.chamadas: list[str] = []
        self.trechos: list[dict] = []

    def _registrar(self, nome: str):
        self.chamadas.append(nome)
        if self.falha:
            raise self.falha

    def classify(self, pergunta: str) -> Classificacao:
        self._registrar("classify")
        if self.classificacao is None:
            return Classificacao(dominio="fora_de_escopo", confianca=0.9)
        return self.classificacao

    def extract_params(self, dominio: str, pergunta: str) -> dict:
        self._registrar("extract_params")
        return dict(self.params)

    def answer(self, pergunta: str, trechos: list[dict]) -> dict:
        self._registrar("answer")
        self.trechos = trechos
        return self.resposta if self.resposta is not None else {"resposta": "", "fontes_usadas": []}
