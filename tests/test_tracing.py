import json

from app import tracing


def test_registro_tem_todos_os_campos(tmp_path):
    tid = tracing.new_trace_id()
    tracing.record_interaction(tmp_path, pergunta="p", dominio_previsto="ouvidoria", confianca=0.9,
                               agente="ouvidoria", fontes=["OUV-0002"], latencia_ms=5, status="ok",
                               modo="degradado")
    linha = json.loads((tmp_path / "interactions.jsonl").read_text(encoding="utf-8"))
    assert set(linha) == set(tracing.CAMPOS)
    assert linha["trace_id"] == tid and linha["fontes"] == ["OUV-0002"] and linha["timestamp"]


def test_find_trace(tmp_path):
    t1 = tracing.new_trace_id()
    tracing.record_interaction(tmp_path, pergunta="a", status="ok")
    t2 = tracing.new_trace_id()
    tracing.record_interaction(tmp_path, pergunta="b", status="ok")
    assert tracing.find_trace(tmp_path, t1)["pergunta"] == "a"
    assert tracing.find_trace(tmp_path, t2)["pergunta"] == "b"
    assert tracing.find_trace(tmp_path, "inexistente") is None


def test_gravacao_com_log_dir_invalido_nao_levanta(tmp_path):
    arquivo = tmp_path / "arquivo"
    arquivo.write_text("x")
    tracing.record_interaction(arquivo / "sub", pergunta="p", status="ok")  # não deve levantar


def test_api_expoe_trace_id_e_grava_log(client, db_settings):
    r = client.post("/ask", json={"pergunta": "Qual o status do protocolo OUV-0002?"})
    tid = r.json()["trace_id"]
    assert r.headers["X-Trace-Id"] == tid
    reg = client.get(f"/traces/{tid}").json()
    assert reg["pergunta"] and reg["dominio_previsto"] == "ouvidoria" and reg["agente"] == "ouvidoria"
    assert reg["fontes"] == ["OUV-0002"] and reg["status"] == "ok" and reg["latencia_ms"] >= 0


def test_falha_registra_erro_com_mesmo_trace_id(client_sem_banco, settings):
    r = client_sem_banco.post("/ask", json={"pergunta": "Qual o status do protocolo OUV-0002?"})
    assert r.status_code == 502
    reg = tracing.find_trace(settings.log_dir, r.json()["trace_id"])
    assert reg["status"] == "erro" and reg["erro"]


def test_trace_desconhecido_404(client):
    assert client.get("/traces/nao-existe").status_code == 404
