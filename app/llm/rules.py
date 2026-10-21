"""Roteamento e extração por regras: modo degradado sem chave de LLM (FR-034)."""
import re
import unicodedata

from app.api.schemas import Classificacao

PROTOCOLO_TOKEN = re.compile(r"\bouv-\w*", re.I)
PROTOCOLO_VALIDO = re.compile(r"\bOUV-\d{4}\b", re.I)

PALAVRAS = {
    "ouvidoria": ["ouvidoria", "protocolo", "manifestacao", "manifestacoes", "reclamacao", "denuncia"],
    "financeiro": ["receita", "despesa", "orcamento", "gasto", "gastos", "lancamento", "financeiro",
                   "inadimplencia", "faturamento", "centro de custo"],
    "informacoes_internas": ["ferias", "reembolso", "politica", "compra", "compras", "phishing",
                             "incidente", "home office", "acesso", "acessos", "privacidade", "procedimento"],
}


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")


def _contem(texto: str, palavra: str) -> bool:
    return re.search(rf"\b{re.escape(palavra)}\b", texto) is not None


class RulesLLM:
    modo = "degradado"

    def classify(self, pergunta: str) -> Classificacao:
        if PROTOCOLO_TOKEN.search(pergunta):
            return Classificacao(dominio="ouvidoria", confianca=0.95, candidatos=["ouvidoria"])
        norm = normalizar(pergunta)
        achados = [d for d, ps in PALAVRAS.items() if any(_contem(norm, p) for p in ps)]
        if len(achados) == 1:
            return Classificacao(dominio=achados[0], confianca=0.8, candidatos=achados)
        if len(achados) > 1:
            return Classificacao(dominio="ambigua", confianca=0.4, candidatos=achados)
        return Classificacao(dominio="fora_de_escopo", confianca=0.6)

    def extract_params(self, dominio: str, pergunta: str) -> dict:
        if dominio != "ouvidoria":
            return {}
        achado = PROTOCOLO_VALIDO.search(pergunta)
        if achado:
            return {"consulta": "buscar_protocolo", "protocolo": achado.group(0).upper()}
        if PROTOCOLO_TOKEN.search(pergunta):
            return {"consulta": "buscar_protocolo", "protocolo": None}  # token com formato inválido
        return {}

    def answer(self, pergunta: str, trechos: list[dict]) -> dict:
        raise NotImplementedError("Resposta redigida por LLM não existe no modo degradado")
