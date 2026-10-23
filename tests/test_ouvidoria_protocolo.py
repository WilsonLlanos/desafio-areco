import pytest


def perguntar(client, texto):
    r = client.post("/ask", json={"pergunta": texto})
    assert r.status_code == 200
    return r.json()


def test_av_t009_status_do_protocolo(client):
    d = perguntar(client, "Qual o status do protocolo OUV-0002?")
    assert d["dominio"] == "ouvidoria" and d["agente"] == "ouvidoria" and d["status"] == "ok"
    assert "Aguardando área responsável" in d["resposta"]
    assert any(f["tipo"] == "protocolo" and f["ref"] == "OUV-0002" for f in d["fontes"])


def test_av_t004_protocolo_inexistente(client):
    d = perguntar(client, "Existe o protocolo OUV-9999?")
    assert d["status"] == "nao_encontrado" and "não foi encontrado" in d["resposta"]
    assert d["dominio"] == "ouvidoria"


def test_protocolo_em_minusculas_e_normalizado(client):
    d = perguntar(client, "status do protocolo ouv-0002")
    assert d["status"] == "ok" and d["fontes"][0]["ref"] == "OUV-0002"


@pytest.mark.parametrize("texto", ["Qual o status do protocolo OUV-12?", "protocolo OUV-00023", "protocolo OUV-"])
def test_formato_invalido_pede_esclarecimento(client, texto):
    d = perguntar(client, texto)
    assert d["status"] == "esclarecimento" and "OUV-NNNN" in d["resposta"]


def test_injecao_sql_no_protocolo_nao_chega_ao_banco(client):
    d = perguntar(client, "protocolo OUV-0002'; DROP TABLE manifestacoes_ouvidoria;--")
    assert d["status"] == "ok"  # só o protocolo válido é extraído; o resto é ignorado
    assert perguntar(client, "status do protocolo OUV-0001")["status"] == "ok"


@pytest.mark.parametrize("protocolo", ["OUV-0002", "OUV-9999"])
def test_busca_por_protocolo_cita_o_arquivo_de_origem(client, protocolo):
    d = client.post("/ask", json={"pergunta": f"Qual o status do protocolo {protocolo}?"}).json()
    assert "manifestacoes.csv" in [f["ref"] for f in d["fontes"]]
