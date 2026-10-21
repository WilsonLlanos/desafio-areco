import json

from app.agents import ouvidoria
from app.queries.ouvidoria import carregar_referencia
from tests import oracle


def perguntar(client, texto):
    r = client.post("/ask", json={"pergunta": texto})
    assert r.status_code == 200, r.text
    return r.json()


def test_av_t005_lista_apenas_status_do_json(client):
    d = perguntar(client, "Quais status podem aparecer na ouvidoria?")
    validos = json.loads((oracle.DATA / "ouvidoria" / "referencia_ouvidoria.json")
                         .read_text(encoding="utf-8-sig"))["status_validos"]
    assert d["status"] == "ok" and d["dominio"] == "ouvidoria"
    assert d["resposta"] == f"Status válidos na ouvidoria: {', '.join(validos)}."
    assert any(f["ref"] == "referencia_ouvidoria.json" for f in d["fontes"])


def test_referencias_de_categorias_prioridades_e_canais(client):
    cats = perguntar(client, "Quais categorias existem na ouvidoria?")["resposta"]
    assert "Produto ou serviço" in cats and "Sugestão" in cats
    prio = perguntar(client, "Quais prioridades são válidas na ouvidoria?")["resposta"]
    assert "Baixa, Média, Alta, Crítica" in prio
    assert "Portal, E-mail, Telefone, Chat" in perguntar(client, "Quais canais existem na ouvidoria?")["resposta"]


def test_contagem_por_status(client):
    d = perguntar(client, "Quantas manifestações estão em análise?")
    assert d["status"] == "ok" and f"Há {len(oracle.ouvidoria(status='Em análise'))} " in d["resposta"]


def test_respondido_e_concluido_sao_distintos(client):
    r = perguntar(client, "Quantas manifestações estão respondidas?")["resposta"]
    c = perguntar(client, "Quantas manifestações estão concluídas?")["resposta"]
    assert f"Há {len(oracle.ouvidoria(status='Respondido'))} " in r
    assert f"Há {len(oracle.ouvidoria(status='Concluído'))} " in c
    assert "status Respondido" in r and "status Concluído" in c


def test_contagem_com_varios_filtros(client):
    d = perguntar(client, "Quantas manifestações da categoria Reembolso com prioridade alta?")
    esperado = len(oracle.ouvidoria(categoria="Reembolso", prioridade="Alta"))
    assert f"Há {esperado} " in d["resposta"] and d["dominio"] == "ouvidoria"


def test_contagem_por_canal_e_periodo(client):
    d = perguntar(client, "Quantas manifestações chegaram pelo canal Chat em 2026?")
    assert f"Há {len(oracle.ouvidoria(canal_entrada='Chat', abertura='2026'))} " in d["resposta"]
    d = perguntar(client, "Quantas manifestações foram abertas em janeiro de 2026?")
    assert f"Há {len(oracle.ouvidoria(abertura='2026-01'))} " in d["resposta"]


def test_lista_limitada_a_10_com_total(client):
    d = perguntar(client, "Liste as manifestações com status Concluído")
    todos = oracle.ouvidoria(status="Concluído")
    assert len(todos) > 10, "o teste precisa de mais de 10 registros"
    protocolos = [f["ref"] for f in d["fontes"] if f["tipo"] == "protocolo"]
    assert protocolos == [r["protocolo"] for r in todos[:10]]
    assert f"{len(todos)} manifestação(ões)" in d["resposta"] and "Mostrando as 10 primeiras" in d["resposta"]
    assert d["resposta"].count("\n- OUV-") == 10


def test_lista_curta_mostra_todos_sem_aviso(client):
    todos = oracle.ouvidoria(categoria="Elogio", prioridade="Crítica")
    d = perguntar(client, "Liste as manifestações da categoria Elogio com prioridade crítica")
    if todos:
        assert len(todos) <= 10 and d["resposta"].count("\n- OUV-") == len(todos)
        assert "Mostrando" not in d["resposta"]
    else:
        assert d["status"] == "nao_encontrado"


def test_lista_vazia_nao_inventa(conn):
    ref = carregar_referencia(oracle.DATA)
    r = ouvidoria.responder(conn, {"consulta": "listar", "status": "Aberto", "categoria": "Elogio",
                                   "prioridade": "Crítica", "canal": "Telefone",
                                   "data_de": "2025-01-01", "data_ate": "2025-01-02"}, ref)
    assert r.status == "nao_encontrado" and "Nenhuma manifestação" in r.resposta


def test_valor_fora_da_referencia_pede_esclarecimento(conn):
    ref = carregar_referencia(oracle.DATA)
    r = ouvidoria.responder(conn, {"consulta": "contar", "status": "Cancelado"}, ref)
    assert r.status == "esclarecimento" and "Aberto, Em análise" in r.resposta


def test_consulta_desconhecida_pede_esclarecimento(conn):
    r = ouvidoria.responder(conn, {"consulta": "apagar"}, carregar_referencia(oracle.DATA))
    assert r.status == "esclarecimento"


def test_protocolo_respondido_mostra_data_de_resposta_distinta(client):
    r = next(x for x in oracle.OUV if x["data_resposta"])
    d = perguntar(client, f"Qual o status do protocolo {r['protocolo']}?")
    abertura = "/".join(reversed(r["data_abertura"].split("-")))
    resposta = "/".join(reversed(r["data_resposta"].split("-")))
    assert f"Aberto em {abertura}" in d["resposta"] and f"data de resposta: {resposta}" in d["resposta"]
    assert "demonstrativo, não um prazo legal" in d["resposta"]


def test_aberto_como_status_difere_de_aberta_em_uma_data(client):
    status = perguntar(client, "Quantas manifestações estão com status aberto?")["resposta"]
    assert f"Há {len(oracle.ouvidoria(status='Aberto'))} " in status and "status Aberto" in status
    por_data = perguntar(client, "Quantas manifestações foram abertas em 2025?")["resposta"]
    assert "status Aberto" not in por_data and f"Há {len(oracle.ouvidoria(abertura='2025'))} " in por_data
