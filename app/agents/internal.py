"""Agente de informações internas: responde só com o texto dos documentos e do FAQ (FR-006, FR-008).

Sem LLM, a resposta é extrativa: a resposta do FAQ, as linhas do documento que casam com a pergunta
ou, se a pergunta tem um valor em reais, a linha da faixa de valor correspondente. Valores e prazos
saem copiados do documento.

Com LLM, o modelo redige a partir dos trechos recuperados (delimitados como dados). A redação é
descartada, voltando à extrativa, se citar fonte fora dos trechos ou um número que não está neles
(FR-008). Faixa de valor continua extrativa: a escolha da faixa é feita por código.
"""
import re
from decimal import Decimal, InvalidOperation

from app.agents.base import Resultado
from app.llm import contratos
from app.api.schemas import Fonte
from app.guards import FONTE_TERCEIROS, MSG_TERCEIROS, TERCEIROS
from app.rag.index import ESCORE_MINIMO, Indice, Item
from app.texto import normalizar, termos

_NUM = r"([\d.]+(?:,\d{1,2})?)"
_VALOR = r"R\$\s*" + _NUM          # na pergunta original
_VALOR_N = r"r\$\s*" + _NUM        # no texto normalizado (minúsculas)


def _decimal(txt: str) -> Decimal | None:
    try:
        return Decimal(txt.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def linhas_do_documento(texto: str) -> list[str]:
    """Linhas de conteúdo, sem título, versão, cabeçalhos e instruções dirigidas ao agente."""
    linhas, secao = [], ""
    for bruta in texto.splitlines():
        l = bruta.strip()
        if l.startswith("## "):
            secao = normalizar(l)
            continue
        if not l or l.startswith("# ") or "Documento fictício" in l or "limites do agente" in secao:
            continue
        l = re.sub(r"^(?:-|\d+\.)\s+", "", l).replace("**", "").strip()
        if re.search(r"\bo agente\b", normalizar(l)):
            continue
        linhas.append(l)
    return linhas


def _faixa_de_valor(linhas: list[str], valor: Decimal) -> list[str]:
    """Linhas "Até R$ X", "De R$ A a R$ B" e "acima de R$ X" que contêm o valor perguntado."""
    achadas = []
    for l in linhas:
        n = normalizar(l)
        if m := re.search(r"\bde " + _VALOR_N + r" a " + _VALOR_N, n):
            a, b = _decimal(m.group(1)), _decimal(m.group(2))
            ok = a is not None and b is not None and a <= valor <= b
        elif m := re.search(r"\bacima de " + _VALOR_N, n):
            a = _decimal(m.group(1))
            ok = a is not None and valor > a
        elif m := re.search(r"\bate " + _VALOR_N, n):
            a = _decimal(m.group(1))
            ok = a is not None and valor <= a
        else:
            continue
        if ok:
            achadas.append(l)
    return achadas


def _alertas(linhas: list[str], excluir: set[int] = frozenset()) -> list[int]:
    """Índice da 1ª linha de proibição ("Não…"/"Nunca…") do documento, se não estiver em `excluir`."""
    return [i for i, l in enumerate(linhas) if re.match(r"(não|nunca)\b", l, re.I) and i not in excluir][:1]


def _linhas_relevantes(linhas: list[str], pergunta: str) -> list[str]:
    consulta = set(termos(pergunta))
    pontuadas = [(len(consulta & set(termos(l))), i) for i, l in enumerate(linhas)]
    escolhidas = sorted(i for p, i in sorted(pontuadas, reverse=True)[:2] if p > 0)
    return [linhas[i] for i in escolhidas] + [f"Atenção: {linhas[i]}" for i in _alertas(linhas, set(escolhidas))]


def _fonte(item: Item, doc: Item | None) -> Fonte:
    versao = (doc or item).document_version
    detalhe = f"{item.id} (faq_interno.json); versão {versao}" if item.tipo == "faq" else f"{item.secao}; versão {versao}"
    return Fonte(tipo="arquivo", ref=item.source, detalhe=detalhe)


# Limites descritos nos próprios documentos (FR-007): checados antes da busca, em ordem.
_LIMITES = [
    (TERCEIROS, FONTE_TERCEIROS, MSG_TERCEIROS),  # mesma regra da guarda pré-LLM
    (re.compile(r"\bsaldo\b.{0,25}\bferias\b|\bferias\b.{0,25}\bsaldo\b|\bquantos dias de ferias\b"),
     "01_politica_ferias.md",
     "Não tenho acesso ao saldo individual de férias. Consulte o RH pelo canal rh@aurora.example."),
    (re.compile(r"\b(holerite|contracheque|meu salario|minha remuneracao)\b"),
     "08_faq_rh.md",
     "Não tenho acesso a registros pessoais, como holerite ou salário. Procure o RH pelo canal "
     "rh@aurora.example."),
    (re.compile(r"\b(trabalhista|rescisao|processar a empresa|meus direitos)\b"),
     "01_politica_ferias.md",
     "Não interpreto situações trabalhistas individuais. Encaminhe o caso ao RH pelo canal rh@aurora.example."),
]


def limite(pergunta: str) -> Resultado | None:
    """Resposta de encaminhamento quando a pergunta pede algo que os documentos proíbem responder."""
    norm = normalizar(pergunta)
    for padrao, arquivo, texto in _LIMITES:
        if padrao.search(norm):
            return Resultado(f"{texto} (Fonte: {arquivo}.)", "recusado",
                             [Fonte(tipo="arquivo", ref=arquivo, detalhe="limites de resposta")])
    return None


_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")


def _numeros(texto: str) -> set[str]:
    return {n.replace(".", "").replace(",", "") for n in _NUMERO.findall(texto)}


def _trechos(indice: Indice, achados: list[tuple[Item, float]]) -> list[dict]:
    """Itens recuperados como dados para o LLM; documentos sem as linhas dirigidas ao agente."""
    trechos = []
    for item, escore in achados:
        if escore < ESCORE_MINIMO / 2:
            continue
        texto = item.texto if item.tipo == "faq" else "\n".join(linhas_do_documento(item.texto))
        trechos.append({"source": item.source, "item": item, "texto": texto})
    return trechos


def redigir(llm, pergunta: str, trechos: list[dict], indice: Indice) -> Resultado | None:
    """Resposta redigida pelo LLM, ou None se ela não passar nas checagens."""
    bruto = llm.answer(pergunta, [{"source": t["source"], "texto": t["texto"]} for t in trechos])
    r = contratos.validar_resposta(bruto, {t["source"] for t in trechos})
    if r is None:
        return None
    if re.match(r"\s*n[ãa]o encontrei", r.resposta, re.I):  # o modelo não achou nos trechos: sem fonte
        return Resultado(r.resposta.strip(), "nao_encontrado", dados={"redigida": True})
    if not _numeros(r.resposta) <= _numeros(" ".join(t["texto"] for t in trechos) + " " + pergunta):
        return None  # número que não está nos trechos: possível invenção
    usadas = list(dict.fromkeys(r.fontes_usadas))
    por_fonte = {t["source"]: t["item"] for t in reversed(trechos)}  # o de maior escore prevalece
    fontes = [_fonte(por_fonte[s], indice.documento(s)) for s in usadas]
    texto = r.resposta.strip()
    # a proibição do documento principal não pode sumir na paráfrase (AV-T012): o código a acrescenta
    doc = indice.documento(trechos[0]["source"])
    linhas = linhas_do_documento(doc.texto) if doc else []
    for i in _alertas(linhas):
        if not set(termos(linhas[i])) <= set(termos(texto)):
            texto += f" Atenção: {linhas[i]}"
    return Resultado(f"{texto} (Fonte: {', '.join(usadas)}.)", "ok", fontes,
                     {"item": por_fonte[usadas[0]].id, "redigida": True})


def responder(indice: Indice, pergunta: str, llm=None) -> Resultado:
    """`llm` opcional: com ele, a resposta é redigida; falha na redação levanta a exceção do provedor."""
    if (r := limite(pergunta)) is not None:
        return r
    achados = indice.buscar(pergunta)
    if not achados or achados[0][1] < ESCORE_MINIMO:
        return Resultado("Não encontrei essa informação nos documentos internos disponíveis. "
                         "Reformule a pergunta ou procure o canal responsável (RH, TI ou Financeiro).",
                         "nao_encontrado", dados={"escores": [(i.id, s) for i, s in achados]})
    item, escore = achados[0]
    doc = indice.documento(item.source)
    linhas = linhas_do_documento(doc.texto) if doc else []
    valor = re.search(_VALOR, pergunta)
    faixa = _faixa_de_valor(linhas, _decimal(valor.group(1))) if valor and _decimal(valor.group(1)) else []
    if llm is not None and not faixa:
        if (r := redigir(llm, pergunta, _trechos(indice, achados), indice)) is not None:
            return r
    if faixa:
        texto = " ".join(faixa)
    elif item.tipo == "faq":
        texto = item.texto.split("\n", 1)[1]
    else:
        texto = " ".join(_linhas_relevantes(linhas, pergunta)) or " ".join(linhas[:2])
    return Resultado(f"{texto} (Fonte: {item.source}.)", "ok", [_fonte(item, doc)],
                     {"item": item.id, "escore": escore})
