import json

import pytest

from app.agents import internal
from app.rag.index import ESCORE_MINIMO, Indice
from tests import oracle


@pytest.fixture(scope="module")
def indice():
    return Indice(oracle.DATA)


CASOS = {c["id"]: c for c in json.loads((oracle.DATA / "testes" / "perguntas_avaliacao.json")
                                          .read_text(encoding="utf-8-sig"))["casos"]}

# Conteúdo-chave exigido pelo critério de cada caso, copiado dos documentos.
CHAVES = {
    "T001": ["portal interno", "30 dias corridos"],
    "T002": ["10 dias corridos", "comprovante"],
    "T003": ["liderança", "gerente", "diretoria"],
    "T008": ["seguranca@aurora.example", "imediatamente"],
    "T012": ["imediatamente", "seguranca@aurora.example", "Não inclua senhas"],
}


def test_indice_tem_17_itens_com_metadados(indice):
    assert len(indice.itens) == 17 and indice.descartados == []
    assert {i.tipo for i in indice.itens} == {"documento", "faq"}
    for item in indice.itens:
        assert item.domain == "informacoes_internas" and item.source.endswith(".md")
        assert item.document_version != "n/d"
    assert indice.documento("01_politica_ferias.md").document_version == "1.2 (10/01/2026)"


def test_faq_aponta_para_o_documento_de_origem(indice):
    faq = {i.id: i for i in indice.itens if i.tipo == "faq"}
    assert len(faq) == 7 and faq["FAQ-001"].source == "01_politica_ferias.md"


@pytest.mark.parametrize("caso", sorted(CHAVES))
def test_casos_de_avaliacao_internos(indice, caso):
    c = CASOS[caso]
    r = internal.responder(indice, c["pergunta"])
    assert r.status == "ok"
    assert [f.ref for f in r.fontes] == [c["fonte_esperada"]]
    for chave in CHAVES[caso]:
        assert chave in r.resposta, f"{caso}: falta '{chave}' em {r.resposta!r}"


@pytest.mark.parametrize("valor,esperado", [
    ("R$ 1.000", "Até R$ 2.000"), ("R$ 2.000", "Até R$ 2.000"), ("R$ 2.000,01", "De R$ 2.000,01 a R$ 10.000"),
    ("R$ 10.000", "De R$ 2.000,01 a R$ 10.000"), ("R$ 10.000,01", "Acima de R$ 10.000"),
])
def test_alcada_de_compra_pela_faixa_de_valor(indice, valor, esperado):
    r = internal.responder(indice, f"Quem aprova uma compra de {valor}?")
    assert r.resposta.startswith(esperado) and r.fontes[0].ref == "03_aprovacao_de_compras.md"


def test_valores_citados_estao_no_texto_do_documento(indice):
    """FR-008: o que a resposta afirma é texto do documento ou do FAQ, não do modelo."""
    for caso in CHAVES:
        r = internal.responder(indice, CASOS[caso]["pergunta"])
        corpo = r.resposta.rsplit(" (Fonte:", 1)[0].removeprefix("Atenção: ")
        textos = [i.texto for i in indice.itens]
        for trecho in corpo.split(" Atenção: "):
            assert any(trecho in t.replace("**", "") or trecho in t for t in textos), trecho


def test_fonte_traz_secao_e_versao(indice):
    r = internal.responder(indice, "O que fazer se houver incidente de segurança?")
    assert r.fontes[0].detalhe == "Registro e tratamento de incidentes; versão 1.0 (12/03/2026)"


@pytest.mark.parametrize("texto", ["Qual a capital da França?", "Quanto custa um café?", "Me conte uma piada"])
def test_sem_resposta_na_base_nao_inventa(indice, texto):
    r = internal.responder(indice, texto)
    assert r.status == "nao_encontrado" and r.fontes == []


def test_escore_minimo_separa_dominio_de_fora_de_escopo(indice):
    for caso in CHAVES:
        assert indice.buscar(CASOS[caso]["pergunta"])[0][1] >= ESCORE_MINIMO
    assert not indice.buscar("Qual a previsão do tempo amanhã?")


def test_linhas_de_limite_nao_vao_para_a_resposta():
    texto = (oracle.DATA / "informacoes_internas" / "01_politica_ferias.md").read_text(encoding="utf-8-sig")
    linhas = internal.linhas_do_documento(texto)
    assert not any("saldo individual" in l for l in linhas) and any("30 dias corridos" in l for l in linhas)


def test_pela_api_dominio_agente_e_fonte(client_sem_banco):
    for caso in CHAVES:
        c = CASOS[caso]
        d = client_sem_banco.post("/ask", json={"pergunta": c["pergunta"]}).json()
        assert d["dominio"] == "informacoes_internas" and d["agente"] == "informacoes_internas"
        assert d["fontes"][0]["ref"] == c["fonte_esperada"] and d["fontes"][0]["tipo"] == "arquivo"


@pytest.mark.parametrize("pergunta,fonte", [
    ("Qual a política de home office?", "06_politica_home_office.md"),  # termo só no nome do arquivo
    ("Qual a política de reembolso?", "02_politica_reembolso.md"),
])
def test_nome_do_arquivo_conta_e_palavras_genericas_nao(indice, pergunta, fonte):
    assert internal.responder(indice, pergunta).fontes[0].ref == fonte
    assert internal.responder(indice, "Qual a política de viagens internacionais?").status == "nao_encontrado"
