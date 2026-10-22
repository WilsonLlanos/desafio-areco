from decimal import Decimal

import pytest

from app.agents import financeiro
from app.agents.base import brl
from tests import oracle


def perguntar(client, texto):
    r = client.post("/ask", json={"pergunta": texto})
    assert r.status_code == 200, r.text
    return r.json()


def test_av_t006_despesas_pagas_jan_mar_2025(client):
    d = perguntar(client, "Quanto foi gasto em despesas pagas no período de janeiro a março de 2025?")
    total, n = oracle.soma("Despesa", 2025, 1, 3, status="Pago")
    assert d["dominio"] == "financeiro" and d["agente"] == "financeiro" and d["status"] == "ok"
    assert brl(total) in d["resposta"] and f"{n} lançamentos" in d["resposta"]
    for critério in ("tipo Despesa", "status Pago", "competência", "janeiro a março de 2025"):
        assert critério in d["resposta"]
    assert {f["tipo"] for f in d["fontes"]} >= {"consulta", "arquivo", "lancamento"}


def test_av_t011_soma_receitas_2025(client):
    d = perguntar(client, "Qual foi a soma de todas as receitas registradas em 2025?")
    total, _ = oracle.soma("Receita", 2025)
    assert d["status"] == "ok" and brl(total) in d["resposta"]
    assert "tipo Receita" in d["resposta"] and "competência" in d["resposta"] and "2025" in d["resposta"]


def test_av_t007_maior_orcamento_jan_2026(client):
    d = perguntar(client, "Qual departamento tem maior orçamento em janeiro de 2026?")
    por_depto = oracle.orcamento_por_departamento(2026, 1)
    maior = max(por_depto.values())
    vencedores = [k for k, v in por_depto.items() if v == maior]
    assert d["status"] == "ok" and d["dominio"] == "financeiro"
    assert all(v in d["resposta"] for v in vencedores) and brl(maior) in d["resposta"]
    assert any(f["ref"] == "orcamento_mensal.csv" for f in d["fontes"])


def test_gasto_sem_criterio_assume_incorrida_e_declara(client):
    d = perguntar(client, "Quanto foi gasto em 2025?")
    total, _ = oracle.soma("Despesa", 2025)  # todos os status
    assert brl(total) in d["resposta"]
    assert "despesa incorrida" in d["resposta"] and "não especificou" in d["resposta"]


def test_paga_difere_de_incorrida(client):
    paga = perguntar(client, "Quanto foi gasto em despesas pagas em 2025?")
    incorrida = perguntar(client, "Quanto foi gasto em despesas incorridas em 2025?")
    tp, _ = oracle.soma("Despesa", 2025, status="Pago")
    ti, _ = oracle.soma("Despesa", 2025)
    assert tp != ti
    assert brl(tp) in paga["resposta"] and brl(ti) in incorrida["resposta"]
    assert "não especificou" not in incorrida["resposta"]  # critério explícito: sem aviso de padrão


def test_competencia_difere_de_vencimento(client):
    comp = perguntar(client, "Qual o total de despesas em janeiro de 2025?")
    venc = perguntar(client, "Qual o total de despesas com vencimento em janeiro de 2025?")
    tc, _ = oracle.soma("Despesa", 2025, 1, 1)
    tv, _ = oracle.soma("Despesa", 2025, 1, 1, campo="data_vencimento")
    assert brl(tc) in comp["resposta"] and "competência" in comp["resposta"]
    assert brl(tv) in venc["resposta"] and "vencimento" in venc["resposta"]


@pytest.mark.parametrize("texto", ["Quanto gastamos em 2024?", "Qual a receita de 2027?"])
def test_ano_fora_de_2025_2026(client, texto):
    d = perguntar(client, texto)
    assert d["status"] == "nao_encontrado" and "2025 a 2026" in d["resposta"]


@pytest.mark.parametrize("texto", ["Qual o total de despesas?", "Qual a inadimplência?",
                                   "Quanto gastamos em março?"])
def test_periodo_ausente_pede_esclarecimento(client, texto):
    d = perguntar(client, texto)
    assert d["status"] == "esclarecimento" and "período" in d["resposta"]
    assert d["fontes"] == []


def test_receita_liquida_igual_a_soma_das_receitas_com_aviso(client):
    d = perguntar(client, "Qual a receita líquida de 2025?")
    total, _ = oracle.soma("Receita", 2025)
    assert d["status"] == "ok" and brl(total) in d["resposta"]
    assert "Receita líquida" in d["resposta"] and "Não há deduções registradas" in d["resposta"]


def test_execucao_orcamentaria(conn):
    r = financeiro.responder(conn, {"consulta": "execucao_orcamentaria", "ano": 2025, "mes_inicio": 1,
                                    "mes_fim": 6})
    gasto, _ = oracle.soma("Despesa", 2025, 1, 6, status="Pago")
    orc = oracle.orcamento(2025, 1, 6)
    assert r.dados["despesas"] == gasto and r.dados["orcamento"] == orc
    assert r.dados["percentual"] == (gasto / orc * 100).quantize(Decimal("0.01"))
    assert "despesas pagas" in r.resposta


def test_execucao_por_departamento(conn):
    r = financeiro.responder(conn, {"consulta": "execucao_orcamentaria", "ano": 2025, "departamento": "tecnologia"})
    gasto, _ = oracle.soma("Despesa", 2025, status="Pago", departamento="Tecnologia")
    assert r.dados["despesas"] == gasto and r.dados["orcamento"] == oracle.orcamento(2025, 1, 12, "Tecnologia")
    assert "departamento Tecnologia" in r.resposta


def test_inadimplencia(conn):
    r = financeiro.responder(conn, {"consulta": "inadimplencia", "ano": 2025})
    atrasado, _ = oracle.soma("Receita", 2025, status="Atrasado")
    total, _ = oracle.soma("Receita", 2025)
    assert r.dados["atrasado"] == atrasado and r.dados["receitas"] == total


def test_comparar_periodos(client):
    d = perguntar(client, "Compare as despesas de 2025 e 2026")
    a, _ = oracle.soma("Despesa", 2025)
    b, _ = oracle.soma("Despesa", 2026)
    assert d["status"] == "ok" and brl(a) in d["resposta"] and brl(b) in d["resposta"]
    assert brl(b - a) in d["resposta"]


def test_filtros_departamento_e_centro_de_custo(client):
    d = perguntar(client, "Quanto foi gasto em despesas pagas de Tecnologia em 2025?")
    total, _ = oracle.soma("Despesa", 2025, status="Pago", departamento="Tecnologia")
    assert brl(total) in d["resposta"] and "departamento Tecnologia" in d["resposta"]
    d = perguntar(client, "Qual o total de despesas do centro de custo CC200 em 2025?")
    total, _ = oracle.soma("Despesa", 2025, centro_custo="CC200")
    assert brl(total) in d["resposta"] and "centro de custo CC200" in d["resposta"]


def test_trimestre(client):
    d = perguntar(client, "Qual o total de receitas no primeiro trimestre de 2025?")
    total, _ = oracle.soma("Receita", 2025, 1, 3)
    assert brl(total) in d["resposta"] or "Não há receitas" in d["resposta"]


def test_fontes_limitadas_a_10_lancamentos(client):
    d = perguntar(client, "Qual o total de despesas em 2025?")
    assert len([f for f in d["fontes"] if f["tipo"] == "lancamento"]) == 10


def test_parametros_invalidos_viram_esclarecimento(conn):
    assert financeiro.responder(conn, {"consulta": "drop_table", "ano": 2025}).status == "esclarecimento"
    assert financeiro.responder(conn, {"consulta": "soma_despesas", "ano": 2025, "sql": "1=1"}).status == "esclarecimento"
    r = financeiro.responder(conn, {"consulta": "soma_despesas", "ano": 2025, "centro_custo": "CC999"})
    assert r.status == "esclarecimento"


def test_departamento_malicioso_nao_chega_ao_sql(conn):
    r = financeiro.responder(conn, {"consulta": "soma_despesas", "ano": 2025,
                                    "departamento": "x'; DROP TABLE lancamentos_financeiros;--"})
    assert r.status == "esclarecimento" and "não existe" in r.resposta
    assert financeiro.responder(conn, {"consulta": "soma_despesas", "ano": 2025}).status == "ok"
