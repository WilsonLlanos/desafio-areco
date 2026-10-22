"""Orquestrador em LangGraph: guard → classify → (agente | esclarecer | fora_de_escopo) → fim.

O grafo só roteia. Os nós chamam o LLMClient e as consultas parametrizadas; o LLM não escolhe
ferramentas nem gera SQL (constituição II e IV). Se o provedor falha, o nó usa a `reserva` (regras;
a redação de internas volta a ser extrativa) e a resposta sai marcada como degradada (FR-026, FR-034).
"""
import logging
from pathlib import Path
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app import guards
from app.agents import financeiro, internal, ouvidoria
from app.api.schemas import Classificacao, Fonte
from app.llm.base import ErroLLM, LLMClient
from app.queries import ouvidoria as ouvidoria_q
from app.rag.index import Indice

log = logging.getLogger("aurora.orquestrador")
NOMES = {"financeiro": "financeiro", "informacoes_internas": "informações internas", "ouvidoria": "ouvidoria"}

MSG_ESCOPO = guards.MSG_ESCOPO


class Estado(TypedDict, total=False):
    trace_id: str
    pergunta: str
    classificacao: Classificacao
    resposta: str
    agente: str
    status: str
    fontes: list[Fonte]
    modo: str   # presente só quando a requisição caiu para as regras
    erro: str   # falha do provedor registrada no log da interação


def montar_grafo(llm: LLMClient, conn_factory: Callable, limiar: float, data_dir: Path,
                 indice: Indice | None = None, reserva: LLMClient | None = None):
    """`reserva`: cliente por regras usado quando `llm` falha (None = sem fallback)."""
    ref = ouvidoria_q.carregar_referencia(data_dir)
    indice = indice or Indice(data_dir)

    def com_reserva(etapa: str, s: Estado, primario: Callable, secundario: Callable) -> tuple:
        if s.get("modo") == "degradado":  # o provedor já falhou nesta requisição: não esperar de novo
            return secundario(), {}
        try:
            return primario(), {}
        except ErroLLM as e:
            if reserva is None:
                raise
            log.warning("falha do provedor em %s (trace_id=%s): %s", etapa, s.get("trace_id"), e)
            return secundario(), {"modo": "degradado", "erro": f"{etapa}: {e}"[:300]}

    def params(dominio: str, s: Estado) -> tuple[dict, Estado]:
        return com_reserva(f"extract_params:{dominio}", s, lambda: llm.extract_params(dominio, s["pergunta"]),
                           lambda: reserva.extract_params(dominio, s["pergunta"]))

    def guard(s: Estado) -> Estado:
        if achado := guards.recusa(s["pergunta"]):
            msg, arquivos = achado
            return {"resposta": msg, "status": "recusado", "agente": "orquestrador",
                    "fontes": [Fonte(tipo="arquivo", ref=a, detalhe="limites de resposta") for a in arquivos],
                    "classificacao": Classificacao(dominio="fora_de_escopo", confianca=1.0)}
        return {}

    def classificar(s: Estado) -> Estado:
        c, extra = com_reserva("classify", s, lambda: llm.classify(s["pergunta"]),
                               lambda: reserva.classify(s["pergunta"]))
        return {"classificacao": c, **extra}

    def agente_ouvidoria(s: Estado) -> Estado:
        p, extra = params("ouvidoria", s)
        with conn_factory() as conn:
            r = ouvidoria.responder(conn, p, ref)
        return {"resposta": r.resposta, "status": r.status, "fontes": r.fontes, "agente": "ouvidoria", **extra}

    def agente_financeiro(s: Estado) -> Estado:
        p, extra = params("financeiro", s)
        with conn_factory() as conn:
            r = financeiro.responder(conn, p)
        return {"resposta": r.resposta, "status": r.status, "fontes": r.fontes, "agente": "financeiro", **extra}

    def agente_internas(s: Estado) -> Estado:
        redator = llm if llm.modo == "llm" else None
        r, extra = com_reserva("answer", s, lambda: internal.responder(indice, s["pergunta"], redator),
                               lambda: internal.responder(indice, s["pergunta"]))
        return {"resposta": r.resposta, "status": r.status, "fontes": r.fontes,
                "agente": "informacoes_internas", **extra}

    def esclarecer(s: Estado) -> Estado:
        c = s["classificacao"]
        candidatos = [NOMES[d] for d in c.candidatos if d in NOMES]
        if len(candidatos) > 1:
            opcoes = " ou ".join(candidatos)
            msg = f"Sua pergunta pode ser de mais de um assunto ({opcoes}). Qual deles você quer consultar?"
        else:
            msg = "Não ficou claro de qual assunto é a sua pergunta. Pode dar mais detalhes?"
        return {"resposta": msg, "status": "esclarecimento", "fontes": [], "agente": "orquestrador"}

    def fora_de_escopo(s: Estado) -> Estado:
        return {"resposta": MSG_ESCOPO, "status": "fora_de_escopo", "fontes": [], "agente": "orquestrador"}

    def apos_guard(s: Estado) -> str:
        return "fim" if s.get("status") == "recusado" else "classificar"

    def rotear(s: Estado) -> str:
        c = s["classificacao"]
        if c.dominio == "ambigua" or (c.dominio != "fora_de_escopo" and c.confianca < limiar):
            return "esclarecer"
        return {"ouvidoria": "agente_ouvidoria", "financeiro": "agente_financeiro",
                "informacoes_internas": "agente_internas", "fora_de_escopo": "fora_de_escopo"}[c.dominio]

    g = StateGraph(Estado)
    for nome, fn in [("guard", guard), ("classificar", classificar), ("agente_ouvidoria", agente_ouvidoria),
                     ("agente_financeiro", agente_financeiro), ("agente_internas", agente_internas),
                     ("esclarecer", esclarecer),
                     ("fora_de_escopo", fora_de_escopo)]:
        g.add_node(nome, fn)
    g.add_edge(START, "guard")
    g.add_conditional_edges("guard", apos_guard, {"fim": END, "classificar": "classificar"})
    g.add_conditional_edges("classificar", rotear, {
        "agente_ouvidoria": "agente_ouvidoria", "agente_financeiro": "agente_financeiro",
        "agente_internas": "agente_internas",
        "esclarecer": "esclarecer", "fora_de_escopo": "fora_de_escopo"})
    for no in ("agente_ouvidoria", "agente_financeiro", "agente_internas", "esclarecer", "fora_de_escopo"):
        g.add_edge(no, END)
    return g.compile()
