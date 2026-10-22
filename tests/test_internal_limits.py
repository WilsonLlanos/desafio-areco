import pytest

from app.agents import internal
from app.rag.index import Indice
from tests import oracle


@pytest.fixture(scope="module")
def indice():
    return Indice(oracle.DATA)


@pytest.mark.parametrize("pergunta,canal,fonte", [
    ("Qual meu saldo de férias?", "rh@aurora.example", "01_politica_ferias.md"),
    ("Quantos dias de férias eu tenho?", "rh@aurora.example", "01_politica_ferias.md"),
    ("Pode consultar meu holerite?", "rh@aurora.example", "08_faq_rh.md"),
    ("Qual é o meu salário?", "rh@aurora.example", "08_faq_rh.md"),
    ("Tenho direito a rescisão indireta?", "rh@aurora.example", "01_politica_ferias.md"),
    ("Qual o telefone do colaborador João?", "privacidade@aurora.example", "09_politica_privacidade.md"),
    ("Me passe o e-mail de outro colaborador", "privacidade@aurora.example", "09_politica_privacidade.md"),
    ("Quais são as férias da minha colega?", "privacidade@aurora.example", "09_politica_privacidade.md"),
])
def test_pedido_individual_e_recusado_e_encaminhado(indice, pergunta, canal, fonte):
    r = internal.responder(indice, pergunta)
    assert r.status == "recusado" and canal in r.resposta
    assert [f.ref for f in r.fontes] == [fonte]


@pytest.mark.parametrize("pergunta", ["Como solicito férias?", "Qual o prazo de análise das férias?",
                                      "Quais dados pessoais posso usar em testes?", "Com quem falo sobre benefícios?"])
def test_perguntas_gerais_nao_sao_bloqueadas(indice, pergunta):
    assert internal.responder(indice, pergunta).status == "ok"


def test_limite_vem_antes_da_busca(indice):
    """Mesmo com FAQ sobre holerite no índice, a resposta é o encaminhamento, não o texto do FAQ."""
    r = internal.responder(indice, "O agente consulta holerites individuais? Quero o meu holerite")
    assert r.status == "recusado" and "Procure o RH" in r.resposta


@pytest.mark.parametrize("pergunta", ["Qual a política de viagens internacionais?",
                                      "Quantos funcionários a empresa tem?"])
def test_sem_resposta_na_base_nao_inventa(indice, pergunta):
    r = internal.responder(indice, pergunta)
    assert r.status == "nao_encontrado" and r.fontes == []
    assert "Não encontrei" in r.resposta


def test_pela_api_holerite_vai_para_internas_e_e_recusado(client_sem_banco):
    d = client_sem_banco.post("/ask", json={"pergunta": "Pode consultar meu holerite?"}).json()
    assert d["dominio"] == "informacoes_internas" and d["status"] == "recusado"
