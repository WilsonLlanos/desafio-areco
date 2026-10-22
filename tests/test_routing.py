"""Roteamento com LLM: esclarecimento, fora de escopo, limiar de confiança e modo (FR-002 a FR-005, FR-034)."""
import dataclasses

import pytest
from fastapi.testclient import TestClient

from app.api.schemas import Classificacao
from app.llm.base import FakeLLM
from app.main import create_app


@pytest.fixture()
def perguntar(settings):
    sem_banco = dataclasses.replace(settings, db_host="127.0.0.1", db_port=1)

    def _perguntar(pergunta: str, fake: FakeLLM | None = None) -> dict:
        return TestClient(create_app(sem_banco, llm=fake)).post("/ask", json={"pergunta": pergunta}).json()
    return _perguntar


def test_ambigua_pede_esclarecimento_com_os_candidatos(perguntar):
    fake = FakeLLM(Classificacao(dominio="ambigua", confianca=0.5, candidatos=["financeiro", "ouvidoria"]))
    d = perguntar("Quanto custou o reembolso da reclamação?", fake)
    assert d["status"] == "esclarecimento" and "financeiro ou ouvidoria" in d["resposta"]
    assert fake.chamadas == ["classify"]  # nenhum agente chamado


def test_baixa_confianca_pede_esclarecimento(perguntar):
    fake = FakeLLM(Classificacao(dominio="financeiro", confianca=0.4, candidatos=["financeiro"]))
    d = perguntar("E aquilo lá?", fake)
    assert d["status"] == "esclarecimento" and d["dominio"] == "financeiro" and d["confianca"] == 0.4
    assert fake.chamadas == ["classify"]


def test_limiar_e_inclusivo(perguntar):
    fake = FakeLLM(Classificacao(dominio="informacoes_internas", confianca=0.6),
                   resposta={"resposta": "Use o portal de RH.", "fontes_usadas": ["01_politica_ferias.md"]})
    assert perguntar("Como solicito férias?", fake)["status"] == "ok"


def test_saida_invalida_do_modelo_vira_esclarecimento(perguntar):
    class SaidaQuebrada(FakeLLM):
        def classify(self, pergunta):
            from app.llm.contratos import validar_classificacao
            return validar_classificacao({"dominio": "vendas", "confianca": 2})
    d = perguntar("Qual o faturamento?", SaidaQuebrada())
    assert d["status"] == "esclarecimento"


def test_fora_de_escopo_explica_os_tres_dominios(perguntar):
    d = perguntar("Qual a previsão do tempo amanhã?", FakeLLM(Classificacao(dominio="fora_de_escopo", confianca=0.95)))
    assert d["status"] == "fora_de_escopo" and d["agente"] == "orquestrador"
    for termo in ("financeiro", "informações internas", "ouvidoria"):
        assert termo in d["resposta"]


def test_fora_de_escopo_com_baixa_confianca_nao_vira_esclarecimento(perguntar):
    d = perguntar("Conte uma piada", FakeLLM(Classificacao(dominio="fora_de_escopo", confianca=0.3)))
    assert d["status"] == "fora_de_escopo"


def test_modo_marcado_na_resposta(perguntar):
    assert perguntar("Como solicito férias?")["modo"] == "degradado"  # sem chave: regras
    fake = FakeLLM(Classificacao(dominio="informacoes_internas", confianca=0.9),
                   resposta={"resposta": "Solicite pelo portal de RH.", "fontes_usadas": ["01_politica_ferias.md"]})
    d = perguntar("Como solicito férias?", fake)
    assert d["modo"] == "llm" and d["resposta"].startswith("Solicite pelo portal de RH.")
    assert d["fontes"][0]["ref"] == "01_politica_ferias.md"


def test_sem_chave_usa_regras(settings):
    app = create_app(dataclasses.replace(settings, gemini_api_key=""))
    assert TestClient(app).get("/health").json()["modo"] == "degradado"


def test_com_chave_usa_gemini_sem_chamar_a_rede(settings):
    # criar o cliente não faz requisição; nenhuma pergunta é enviada aqui
    app = create_app(dataclasses.replace(settings, gemini_api_key="chave-de-teste"))
    assert TestClient(app).get("/health").json()["modo"] == "llm"
