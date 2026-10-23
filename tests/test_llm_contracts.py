"""Saídas do LLM são dados não confiáveis: validadas por contrato (contracts/llm-schemas.md)."""
import dataclasses
import json

import pytest
from fastapi.testclient import TestClient

from app.agents import internal
from app.api.schemas import Classificacao
from app.llm import contratos
from app.llm.base import ErroLLM, FakeLLM
from app.main import create_app
from app.orchestrator import montar_grafo
from app.rag.index import Indice
from tests import oracle


@pytest.fixture(scope="module")
def indice():
    return Indice(oracle.DATA)


def _api(settings, fake):
    sem_banco = dataclasses.replace(settings, db_host="127.0.0.1", db_port=1)
    return TestClient(create_app(sem_banco, llm=fake))


# --- classificação -------------------------------------------------------------------------------
@pytest.mark.parametrize("bruto", [
    None, "texto livre", {"dominio": "rh", "confianca": 0.9},
    {"dominio": "financeiro", "confianca": 1.5},
    {"dominio": "financeiro", "confianca": 0.9, "sql": "DROP TABLE x"},
    {"dominio": "financeiro", "confianca": 0.9, "candidatos": ["vendas"]},
])
def test_classificacao_invalida_vira_baixa_confianca(bruto):
    c = contratos.validar_classificacao(bruto)
    assert c.dominio == "ambigua" and c.confianca == 0.0


def test_classificacao_valida_e_preservada():
    c = contratos.validar_classificacao({"dominio": "ouvidoria", "confianca": 0.8, "candidatos": ["ouvidoria"]})
    assert (c.dominio, c.confianca, c.candidatos) == ("ouvidoria", 0.8, ["ouvidoria"])


# --- parâmetros ----------------------------------------------------------------------------------
def test_params_financeiros_invalidos_viram_ausentes():
    p = contratos.validar_params("financeiro", {
        "consulta": "apagar_tudo", "ano": 2025, "mes_inicio": 13, "mes_fim": 3, "centro_custo": "CC900",
        "criterio_gasto": "paga", "sql": "SELECT 1", "tipo_data": None})
    assert p == {"ano": 2025, "mes_fim": 3, "criterio_gasto": "paga"}


def test_params_de_ouvidoria_normalizam_e_descartam():
    p = contratos.validar_params("ouvidoria", {
        "consulta": "buscar_protocolo", "protocolo": " ouv-0002 ", "data_de": "ontem",
        "referencia_tipo": "cor", "status": "Pendente"})
    # o enum de status é conferido pelo agente, que lista os valores válidos
    assert p == {"consulta": "buscar_protocolo", "protocolo": "OUV-0002", "status": "Pendente"}
    assert contratos.validar_params("ouvidoria", {"consulta": "buscar_protocolo", "protocolo": "OUV-12"}) == \
        {"consulta": "buscar_protocolo"}


@pytest.mark.parametrize("bruto", [None, "x", ["ano"], {}])
def test_params_malformados_viram_vazio(bruto):
    assert contratos.validar_params("financeiro", bruto) == {}


def test_protocolo_invalido_do_llm_pede_esclarecimento(conn):
    from app.agents import ouvidoria
    p = contratos.validar_params("ouvidoria", {"consulta": "buscar_protocolo", "protocolo": "OUV-99999"})
    r = ouvidoria.responder(conn, p)
    assert r.status == "esclarecimento" and "OUV-NNNN" in r.resposta


# --- redação de informações internas -------------------------------------------------------------
@pytest.mark.parametrize("bruto", [
    {"resposta": "Use o portal.", "fontes_usadas": ["99_inventado.md"]},
    {"resposta": "Use o portal.", "fontes_usadas": []},
    {"resposta": "", "fontes_usadas": ["01_politica_ferias.md"]},
    {"resposta": "Use o portal.", "fontes_usadas": ["01_politica_ferias.md"], "extra": 1},
    None,
])
def test_redacao_invalida_volta_para_a_extrativa(indice, bruto):
    r = internal.responder(indice, "Como solicito férias?", FakeLLM(resposta=bruto))
    assert r.status == "ok" and "redigida" not in r.dados
    assert [f.ref for f in r.fontes] == ["01_politica_ferias.md"]


def test_numero_inventado_descarta_a_redacao(indice):
    fake = FakeLLM(resposta={"resposta": "Peça as férias com 45 dias de antecedência.",
                             "fontes_usadas": ["01_politica_ferias.md"]})
    r = internal.responder(indice, "Como solicito férias?", fake)
    assert "redigida" not in r.dados and "45" not in r.resposta


def test_redacao_valida_tem_fontes_escritas_pelo_codigo(indice):
    fake = FakeLLM(resposta={"resposta": "Solicite pelo portal de RH com 30 dias de antecedência.",
                             "fontes_usadas": ["01_politica_ferias.md"]})
    r = internal.responder(indice, "Como solicito férias?", fake)
    assert r.dados["redigida"] and r.resposta.endswith("(Fonte: 01_politica_ferias.md.)")
    assert r.fontes[0].ref == "01_politica_ferias.md" and "versão 1.2" in r.fontes[0].detalhe
    # trechos chegam ao modelo sem as linhas dirigidas ao agente
    assert fake.trechos and all("o agente" not in t["texto"].lower() for t in fake.trechos)


def test_limites_e_nao_encontrado_nao_chamam_o_llm(indice):
    fake = FakeLLM()
    assert internal.responder(indice, "Pode consultar meu holerite?", fake).status == "recusado"
    assert internal.responder(indice, "Qual a cotação do dólar hoje?", fake).status == "nao_encontrado"
    assert fake.chamadas == []


def test_faixa_de_valor_continua_extrativa(indice):
    fake = FakeLLM()
    r = internal.responder(indice, "Quais são as aprovações para uma compra de R$ 12.000?", fake)
    assert r.status == "ok" and fake.chamadas == []


# --- falha do provedor ---------------------------------------------------------------------------
def test_falha_do_provedor_cai_para_regras_e_registra_o_erro(settings):
    fake = FakeLLM(falha=ErroLLM("timeout"))
    resp = _api(settings, fake).post("/ask", json={"pergunta": "Como solicito férias?"})
    d = resp.json()
    assert resp.status_code == 200 and d["status"] == "ok" and d["modo"] == "degradado"
    assert d["dominio"] == "informacoes_internas" and d["fontes"][0]["ref"] == "01_politica_ferias.md"
    registros = [json.loads(linha) for linha in (settings.log_dir / "interactions.jsonl").read_text().splitlines()]
    reg = next(r for r in registros if r["trace_id"] == d["trace_id"] == resp.headers["X-Trace-Id"])
    assert reg["modo"] == "degradado" and "timeout" in reg["erro"]
    assert fake.chamadas == ["classify"]


def test_sem_reserva_a_falha_sobe(settings):
    grafo = montar_grafo(FakeLLM(falha=ErroLLM("cota")), None, 0.6, oracle.DATA)
    with pytest.raises(ErroLLM):
        grafo.invoke({"trace_id": "t", "pergunta": "Como solicito férias?"})


def test_classificacao_ok_com_falha_na_redacao(settings):
    class FalhaSoNaRedacao(FakeLLM):
        def answer(self, pergunta, trechos):
            raise ErroLLM("503")
    fake = FalhaSoNaRedacao(Classificacao(dominio="informacoes_internas", confianca=0.9))
    d = _api(settings, fake).post("/ask", json={"pergunta": "Qual o prazo para pedir reembolso?"}).json()
    assert d["status"] == "ok" and d["modo"] == "degradado" and "comprovante" in d["resposta"]


def test_apos_falha_a_requisicao_nao_chama_o_provedor_de_novo(settings):
    fake = FakeLLM(falha=ErroLLM("timeout"))
    d = _api(settings, fake).post("/ask", json={"pergunta": "Como solicito férias?"}).json()
    assert d["modo"] == "degradado" and fake.chamadas == ["classify"]  # sem esperar a redação


def test_nao_encontrei_do_modelo_sai_sem_fonte(indice):
    fake = FakeLLM(resposta={"resposta": "Não encontrei essa informação nos documentos.",
                             "fontes_usadas": ["01_politica_ferias.md"]})
    r = internal.responder(indice, "Como solicito férias?", fake)
    assert r.status == "nao_encontrado" and r.fontes == [] and "Fonte" not in r.resposta


def test_redacao_mantem_a_proibicao_do_documento(indice):
    """AV-T012: o modelo omitiu "Não inclua senhas…"; o código acrescenta a linha de alerta."""
    fake = FakeLLM(resposta={"resposta": "Reporte imediatamente para seguranca@aurora.example.",
                             "fontes_usadas": ["07_fluxo_de_incidentes.md"]})
    r = internal.responder(indice, "O que fazer se houver incidente de segurança?", fake)
    assert r.dados["redigida"] and "Atenção: Não inclua senhas, tokens" in r.resposta
    assert r.resposta.endswith("(Fonte: 07_fluxo_de_incidentes.md.)")


def test_proibicao_ja_coberta_nao_e_repetida(indice):
    fake = FakeLLM(resposta={"resposta": "Reporte imediatamente para seguranca@aurora.example. Não inclua senhas, "
                                         "tokens, dados pessoais desnecessários ou informações sigilosas no chamado.",
                             "fontes_usadas": ["07_fluxo_de_incidentes.md"]})
    r = internal.responder(indice, "O que fazer se houver incidente de segurança?", fake)
    assert "Atenção" not in r.resposta
