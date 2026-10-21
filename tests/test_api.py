import pytest

from app.llm.rules import RulesLLM


@pytest.mark.parametrize("corpo", [{"pergunta": ""}, {"pergunta": "   "}, {"pergunta": "?!?!"},
                                   {"pergunta": "a" * 1001}, {}])
def test_entrada_invalida_422(client_sem_banco, corpo):
    r = client_sem_banco.post("/ask", json=corpo)
    assert r.status_code == 422
    assert r.json()["trace_id"] and r.json()["detail"]


def test_health_sem_banco_continua_respondendo(client_sem_banco):
    r = client_sem_banco.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "banco": "indisponivel", "modo": "degradado"}


def test_banco_indisponivel_devolve_502_claro(client_sem_banco):
    r = client_sem_banco.post("/ask", json={"pergunta": "status do protocolo OUV-0002"})
    assert r.status_code == 502 and "indisponível" in r.json()["detail"]
    # a API segue atendendo perguntas que não precisam do banco
    d = client_sem_banco.post("/ask", json={"pergunta": "Qual a previsão do tempo?"}).json()
    assert d["status"] == "fora_de_escopo"


def test_health_com_banco(client):
    assert client.get("/health").json() == {"status": "ok", "banco": "ok", "modo": "degradado"}


def test_frontend_servido(client):
    r = client.get("/")
    assert r.status_code == 200 and "Assistente Aurora" in r.text


@pytest.mark.parametrize("texto,dominio", [
    ("Como solicito férias?", "informacoes_internas"),
    ("Quanto foi gasto em despesas pagas?", "financeiro"),
    ("Qual o status do protocolo OUV-0002?", "ouvidoria"),
    ("Qual o prazo de reembolso da despesa?", "ambigua"),
    ("Qual a previsão do tempo?", "fora_de_escopo"),
])
def test_regras_de_classificacao(texto, dominio):
    assert RulesLLM().classify(texto).dominio == dominio


def test_dominio_sem_agente_responde_indisponivel(client_sem_banco):
    d = client_sem_banco.post("/ask", json={"pergunta": "Como solicito férias?"}).json()
    assert d["dominio"] == "informacoes_internas" and d["status"] == "erro"
    assert "ainda não está disponível" in d["resposta"]
