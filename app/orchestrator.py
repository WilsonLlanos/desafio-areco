"""Orquestrador em LangGraph: guard → classify → (agente | esclarecer | fora_de_escopo) → fim.

O grafo só roteia. Os nós chamam o LLMClient e as consultas parametrizadas; o LLM não escolhe
ferramentas nem gera SQL (constituição II e IV).
"""
from pathlib import Path
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from app import guards
from app.agents import financeiro, internal, ouvidoria
from app.api.schemas import Classificacao, Fonte
from app.llm.base import LLMClient
from app.queries import ouvidoria as ouvidoria_q
from app.rag.index import Indice

NOMES = {"financeiro": "financeiro", "informacoes_internas": "informações internas", "ouvidoria": "ouvidoria"}

MSG_ESCOPO = ("Só posso ajudar com três assuntos: financeiro (lançamentos e orçamento), informações "
              "internas (políticas e procedimentos) e ouvidoria (protocolos e manifestações). "
              "Reformule a pergunta dentro de um desses temas.")


class Estado(TypedDict, total=False):
    trace_id: str
    pergunta: str
    classificacao: Classificacao
    resposta: str
    agente: str
    status: str
    fontes: list[Fonte]


def montar_grafo(llm: LLMClient, conn_factory: Callable, limiar: float, data_dir: Path,
                 indice: Indice | None = None):
    ref = ouvidoria_q.carregar_referencia(data_dir)
    indice = indice or Indice(data_dir)

    def guard(s: Estado) -> Estado:
        msg = guards.recusa(s["pergunta"])
        if msg:
            return {"resposta": msg, "status": "recusado", "agente": "orquestrador", "fontes": [],
                    "classificacao": Classificacao(dominio="fora_de_escopo", confianca=1.0)}
        return {}

    def classificar(s: Estado) -> Estado:
        return {"classificacao": llm.classify(s["pergunta"])}

    def agente_ouvidoria(s: Estado) -> Estado:
        params = llm.extract_params("ouvidoria", s["pergunta"])
        with conn_factory() as conn:
            r = ouvidoria.responder(conn, params, ref)
        return {"resposta": r.resposta, "status": r.status, "fontes": r.fontes, "agente": "ouvidoria"}

    def agente_financeiro(s: Estado) -> Estado:
        params = llm.extract_params("financeiro", s["pergunta"])
        with conn_factory() as conn:
            r = financeiro.responder(conn, params)
        return {"resposta": r.resposta, "status": r.status, "fontes": r.fontes, "agente": "financeiro"}

    def agente_internas(s: Estado) -> Estado:
        r = internal.responder(indice, s["pergunta"])
        return {"resposta": r.resposta, "status": r.status, "fontes": r.fontes, "agente": "informacoes_internas"}

    def esclarecer(s: Estado) -> Estado:
        c = s["classificacao"]
        if len(c.candidatos) > 1:
            opcoes = " ou ".join(NOMES[d] for d in c.candidatos)
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
