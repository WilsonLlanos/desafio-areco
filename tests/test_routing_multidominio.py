import pytest

from app.api.schemas import Classificacao
from app.llm.base import FakeLLM
from app.orchestrator import montar_grafo
from tests import oracle


def perguntar(client, texto):
    r = client.post("/ask", json={"pergunta": texto})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.mark.parametrize("texto,mencionados", [
    ("Qual o prazo de reembolso da despesa?", ("financeiro", "informações internas")),
    ("Quantas manifestações há e qual o total de despesas de 2025?", ("financeiro", "ouvidoria")),
])
def test_pergunta_que_cruza_dominios_pede_esclarecimento(client, texto, mencionados):
    d = perguntar(client, texto)
    assert d["status"] == "esclarecimento" and d["agente"] == "orquestrador" and d["dominio"] == "ambigua"
    assert d["fontes"] == []
    assert all(m in d["resposta"] for m in mencionados)


def test_categoria_compartilhada_nao_vira_ambiguidade_em_ouvidoria(client):
    d = perguntar(client, "Quantas manifestações de reembolso existem?")
    assert d["dominio"] == "ouvidoria" and d["status"] == "ok"
    assert f"Há {len(oracle.ouvidoria(categoria='Reembolso'))} " in d["resposta"]


def test_grafo_nunca_aciona_agentes_quando_ha_dois_dominios(tmp_path):
    def sem_banco():
        raise AssertionError("nenhum agente deveria consultar o banco")

    llm = FakeLLM(Classificacao(dominio="ambigua", confianca=0.9, candidatos=["financeiro", "ouvidoria"]))
    estado = montar_grafo(llm, sem_banco, 0.6, oracle.DATA).invoke({"trace_id": "t", "pergunta": "x"})
    assert estado["status"] == "esclarecimento" and "financeiro ou ouvidoria" in estado["resposta"]
    assert llm.chamadas == ["classify"]  # sem extração de parâmetros: nenhum agente foi chamado


def test_baixa_confianca_pede_esclarecimento(tmp_path):
    llm = FakeLLM(Classificacao(dominio="financeiro", confianca=0.3, candidatos=["financeiro"]))
    estado = montar_grafo(llm, lambda: None, 0.6, oracle.DATA).invoke({"trace_id": "t", "pergunta": "x"})
    assert estado["status"] == "esclarecimento" and llm.chamadas == ["classify"]
