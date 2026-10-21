"""Agente financeiro. Cálculo determinístico sobre consultas parametrizadas; o LLM não vê nem escreve números.

Critérios (FR-015 a FR-017, indicadores_e_regras.json):
- despesa paga = tipo Despesa e status Pago; incorrida = Despesa em qualquer status;
- gasto sem critério → incorrida, sempre declarado; competência é o padrão de data.
"""
from decimal import Decimal

from pydantic import ValidationError

from app.agents.base import Resultado, brl, esclarecimento, pct
from app.api.schemas import Fonte
from app.periodo import intervalo, rotulo
from app.queries import financeiro as q

ANOS_VALIDOS = (2025, 2026)
ARQ_LANC, ARQ_ORC = "lancamentos_financeiros.csv", "orcamento_mensal.csv"
DEFAULT_GASTO = ("Como a pergunta não especificou se o gasto é pago ou incorrido, considerei despesa "
                 "incorrida (todos os status).")


def _periodo(p: q.ParamsFinanceiro):
    mi = p.mes_inicio or 1
    mf = p.mes_fim or p.mes_inicio or 12
    return mi, mf


def _fontes(consulta: str, criterio: str, arquivo: str, ids: list[str] = ()) -> list[Fonte]:
    return ([Fonte(tipo="consulta", ref=f"financeiro.{consulta}", detalhe=criterio),
             Fonte(tipo="arquivo", ref=arquivo)]
            + [Fonte(tipo="lancamento", ref=i) for i in ids])


def _escopo(p: q.ParamsFinanceiro) -> str:
    partes = []
    if p.departamento:
        partes.append(f"departamento {p.departamento}")
    if p.centro_custo:
        partes.append(f"centro de custo {p.centro_custo}")
    if p.categoria:
        partes.append(f"categoria {p.categoria}")
    return "; ".join(partes)


def _criterio(partes: list[str], p: q.ParamsFinanceiro) -> str:
    escopo = _escopo(p)
    return "; ".join(partes + ([escopo] if escopo else []))


def _status_gasto(p: q.ParamsFinanceiro, padrao: str) -> tuple[str | None, str, bool]:
    """(status SQL, texto do critério, usou_padrão) para despesas."""
    crit = p.criterio_gasto or padrao
    if crit == "paga":
        return "Pago", "tipo Despesa; status Pago (despesa paga)", p.criterio_gasto is None
    return None, "tipo Despesa; todos os status (despesa incorrida)", p.criterio_gasto is None


def _soma(conn, p, tipo, inicio, fim, status, tipo_data):
    return q.somar_lancamentos(conn, tipo=tipo, status=status, tipo_data=tipo_data, inicio=inicio, fim=fim,
                               departamento=p.departamento, centro_custo=p.centro_custo, categoria=p.categoria)


def _soma_lancamentos(conn, p, mi, mf, tipo_data) -> Resultado:
    inicio, fim = intervalo(p.ano, mi, mf)
    per = rotulo(p.ano, mi, mf)
    data_txt = f"data de {'vencimento' if tipo_data == 'vencimento' else 'competência'}"
    if p.consulta == "soma_despesas":
        status, crit_txt, padrao = _status_gasto(p, "incorrida")
        tipo, nome = "Despesa", "despesas"
    else:
        status, crit_txt, padrao = None, "tipo Receita; todos os status", False
        tipo, nome = "Receita", "receitas"
    r = _soma(conn, p, tipo, inicio, fim, status, tipo_data)
    criterio = _criterio([crit_txt, data_txt, f"período {per}"], p)
    fontes = _fontes(p.consulta, criterio, ARQ_LANC, r["ids"])
    dados = {"total": r["total"], "n": r["n"], "criterio": criterio}
    if r["n"] == 0:
        return Resultado(f"Não há {nome} registradas no período ({criterio}).", "nao_encontrado", fontes, dados)
    texto = f"Total de {nome}: {brl(r['total'])} ({r['n']} lançamentos). Critério: {criterio}."
    if padrao:
        texto += " " + DEFAULT_GASTO
    if r["n"] > len(r["ids"]):
        texto += f" Fontes: {len(r['ids'])} de {r['n']} lançamentos listados."
    return Resultado(texto, "ok", fontes, dados)


def _receita_liquida(conn, p, mi, mf, tipo_data) -> Resultado:
    res = _soma_lancamentos(conn, p.model_copy(update={"consulta": "soma_receitas"}), mi, mf, tipo_data)
    if res.status != "ok":
        return res
    aviso = ("Não há deduções registradas na base; por isso a receita líquida é igual à soma das receitas.")
    texto = res.resposta.replace("Total de receitas:", "Receita líquida:", 1) + " " + aviso
    return Resultado(texto, "ok", res.fontes, {**res.dados, "liquida": res.dados["total"]})


def _comparar(conn, p, mi, mf, tipo_data) -> Resultado:
    if p.ano_b is None:
        return esclarecimento("Qual o segundo período da comparação? Informe o ano (e meses, se houver).")
    if p.ano_b not in ANOS_VALIDOS:
        return _fora_do_intervalo(p.ano_b)
    mib, mfb = p.mes_inicio_b or mi, p.mes_fim_b or mf
    tipo, status, nome = ("Receita", None, "receitas") if p.metrica == "receitas" else ("Despesa", None, "despesas")
    a = _soma(conn, p, tipo, *intervalo(p.ano, mi, mf), status, tipo_data)
    b = _soma(conn, p, tipo, *intervalo(p.ano_b, mib, mfb), status, tipo_data)
    per_a, per_b = rotulo(p.ano, mi, mf), rotulo(p.ano_b, mib, mfb)
    dif = b["total"] - a["total"]
    var = f" ({pct(dif, a['total'])} sobre {per_a})" if a["total"] else ""
    criterio = _criterio([f"tipo {tipo}; todos os status", f"data de "
                          f"{'vencimento' if tipo_data == 'vencimento' else 'competência'}",
                          f"períodos {per_a} e {per_b}"], p)
    texto = (f"Comparação de {nome}: {per_a}: {brl(a['total'])}; {per_b}: {brl(b['total'])}. "
             f"Diferença: {brl(dif)}{var}. Critério: {criterio}.")
    return Resultado(texto, "ok", _fontes("comparar_periodos", criterio, ARQ_LANC, a["ids"] + b["ids"]),
                     {"total_a": a["total"], "total_b": b["total"], "diferenca": dif})


def _orcamento(conn, p, mi, mf) -> Resultado:
    linhas = q.orcamento_por_departamento(conn, ano=p.ano, mes_inicio=mi, mes_fim=mf, centro_custo=p.centro_custo)
    per = rotulo(p.ano, mi, mf)
    criterio = _criterio([f"orçamento aprovado somado no período {per}"], p)
    fontes = _fontes("orcamento_por_departamento", criterio, ARQ_ORC)
    if not linhas:
        return Resultado(f"Não há orçamento registrado para o período ({criterio}).", "nao_encontrado", fontes)
    alvo = linhas[-1] if p.ordem == "menor" else linhas[0]
    empatados = [l["departamento"] for l in linhas if l["total"] == alvo["total"]]
    qual = "menor" if p.ordem == "menor" else "maior"
    lista = "; ".join(f"{l['departamento']}: {brl(l['total'])}" for l in linhas)
    texto = (f"{'Departamentos' if len(empatados) > 1 else 'Departamento'} com {qual} orçamento em {per}: "
             f"{', '.join(empatados)} ({brl(alvo['total'])}). Orçamento por departamento: {lista}. "
             f"Critério: {criterio}.")
    return Resultado(texto, "ok", fontes, {"departamentos": empatados, "total": alvo["total"],
                                           "ranking": [(l["departamento"], l["total"]) for l in linhas]})


def _execucao(conn, p, mi, mf, tipo_data) -> Resultado:
    # Indicador definido como "despesas realizadas ÷ orçamento aprovado"; realizadas = pagas.
    status, crit_txt, padrao = _status_gasto(p, "paga")
    inicio, fim = intervalo(p.ano, mi, mf)
    gasto = _soma(conn, p, "Despesa", inicio, fim, status, tipo_data)
    orc = q.orcamento_total(conn, ano=p.ano, mes_inicio=mi, mes_fim=mf, departamento=p.departamento,
                            centro_custo=p.centro_custo)
    per = rotulo(p.ano, mi, mf)
    criterio = _criterio([crit_txt, f"data de {'vencimento' if tipo_data == 'vencimento' else 'competência'}",
                          f"período {per}", "orçamento aprovado do mesmo período"], p)
    fontes = _fontes("execucao_orcamentaria", criterio, f"{ARQ_LANC} e {ARQ_ORC}", gasto["ids"])
    if orc == 0:
        return Resultado(f"Não há orçamento registrado para o período ({criterio}); não é possível "
                         "calcular a execução orçamentária.", "nao_encontrado", fontes)
    texto = (f"Execução orçamentária: {pct(gasto['total'], orc)} (despesas {brl(gasto['total'])} ÷ "
             f"orçamento {brl(orc)}). Critério: {criterio}.")
    if padrao:
        texto += " Como o indicador usa despesas realizadas, considerei despesas pagas."
    return Resultado(texto, "ok", fontes, {"despesas": gasto["total"], "orcamento": orc,
                                           "percentual": (gasto["total"] / orc * 100).quantize(Decimal("0.01"))})


def _inadimplencia(conn, p, mi, mf, tipo_data) -> Resultado:
    inicio, fim = intervalo(p.ano, mi, mf)
    atrasado = _soma(conn, p, "Receita", inicio, fim, "Atrasado", tipo_data)
    total = _soma(conn, p, "Receita", inicio, fim, None, tipo_data)
    per = rotulo(p.ano, mi, mf)
    criterio = _criterio(["tipo Receita; status Atrasado ÷ todas as receitas, em valor",
                          f"data de {'vencimento' if tipo_data == 'vencimento' else 'competência'}",
                          f"período {per}"], p)
    fontes = _fontes("inadimplencia", criterio, ARQ_LANC, atrasado["ids"])
    if total["total"] == 0:
        return Resultado(f"Não há receitas registradas no período ({criterio}).", "nao_encontrado", fontes)
    texto = (f"Inadimplência de recebíveis: {pct(atrasado['total'], total['total'])} "
             f"({brl(atrasado['total'])} atrasados de {brl(total['total'])} em receitas). Critério: {criterio}.")
    return Resultado(texto, "ok", fontes, {"atrasado": atrasado["total"], "receitas": total["total"]})


def _fora_do_intervalo(ano: int) -> Resultado:
    return Resultado(f"A base financeira cobre apenas {ANOS_VALIDOS[0]} a {ANOS_VALIDOS[-1]}; não há dados de {ano}.",
                     "nao_encontrado")


def responder(conn, params: dict) -> Resultado:
    try:
        p = q.ParamsFinanceiro(**params)
    except (ValidationError, TypeError):
        return esclarecimento("Não consegui entender os parâmetros da consulta financeira. "
                              "Informe o que calcular (receitas, despesas, orçamento) e o período.")
    if p.consulta is None:
        return esclarecimento("O que você quer saber do financeiro? Posso somar receitas ou despesas, "
                              "comparar períodos, informar o orçamento por departamento, a execução "
                              "orçamentária e a inadimplência. Informe também o período.")
    if p.ano is None:  # FR-035: nunca assumir o período
        return esclarecimento("Para qual período você quer essa informação? Informe o ano e, se quiser, "
                              "os meses (por exemplo, janeiro a março de 2025).")
    if p.ano not in ANOS_VALIDOS:
        return _fora_do_intervalo(p.ano)
    mi, mf = _periodo(p)
    if mf < mi:
        return esclarecimento("O mês final vem antes do inicial. Pode confirmar o período?")
    if p.departamento:
        validos = {d.lower(): d for d in q.departamentos(conn)}
        if p.departamento.lower() not in validos:
            return esclarecimento(f"Departamento \"{p.departamento}\" não existe. Válidos: "
                                  f"{', '.join(sorted(validos.values()))}.")
        p = p.model_copy(update={"departamento": validos[p.departamento.lower()]})
    tipo_data = p.tipo_data or "competencia"
    despacho = {
        "soma_despesas": lambda: _soma_lancamentos(conn, p, mi, mf, tipo_data),
        "soma_receitas": lambda: _soma_lancamentos(conn, p, mi, mf, tipo_data),
        "receita_liquida": lambda: _receita_liquida(conn, p, mi, mf, tipo_data),
        "comparar_periodos": lambda: _comparar(conn, p, mi, mf, tipo_data),
        "orcamento_por_departamento": lambda: _orcamento(conn, p, mi, mf),
        "execucao_orcamentaria": lambda: _execucao(conn, p, mi, mf, tipo_data),
        "inadimplencia": lambda: _inadimplencia(conn, p, mi, mf, tipo_data),
    }
    return despacho[p.consulta]()
