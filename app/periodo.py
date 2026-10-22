"""Períodos em português: extração de texto normalizado e conversão para intervalos de datas."""
import re
from datetime import date

NOMES_MES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro"]
MESES = {n.replace("ç", "c"): i for i, n in enumerate(NOMES_MES, start=1)}
_ORDINAL = {"primeiro": 1, "segundo": 2, "terceiro": 3, "quarto": 4, "1": 1, "2": 2, "3": 3, "4": 4}
_RE_MES = re.compile(r"\b(" + "|".join(MESES) + r")\b")
_RE_TRI = re.compile(r"\b(primeiro|segundo|terceiro|quarto|[1-4])\s*[ºo°]?\s*trimestre\b")
_RE_SEM = re.compile(r"\b(primeiro|segundo|[12])\s*[ºo°]?\s*semestre\b")


def anos_no_texto(norm: str) -> list[int]:
    return [int(a) for a in re.findall(r"\b(20\d{2})\b", norm)]


def extrair_periodo(norm: str) -> dict:
    """Texto sem acentos e em minúsculas → {ano, mes_inicio, mes_fim} (chaves ausentes se não houver)."""
    out: dict = {}
    anos = anos_no_texto(norm)
    if anos:
        out["ano"] = anos[0]
    if m := _RE_TRI.search(norm):
        n = _ORDINAL[m.group(1)]
        out["mes_inicio"], out["mes_fim"] = 3 * n - 2, 3 * n
    elif m := _RE_SEM.search(norm):
        n = _ORDINAL[m.group(1)]
        out["mes_inicio"], out["mes_fim"] = (1, 6) if n == 1 else (7, 12)
    else:
        meses = [MESES[m.group(1)] for m in _RE_MES.finditer(norm)]
        if meses:
            out["mes_inicio"], out["mes_fim"] = meses[0], meses[-1]
    return out


def intervalo(ano: int, mes_inicio: int, mes_fim: int) -> tuple[date, date]:
    """[início, fim) em datas; o fim é o primeiro dia do mês seguinte ao último mês."""
    fim = date(ano + 1, 1, 1) if mes_fim == 12 else date(ano, mes_fim + 1, 1)
    return date(ano, mes_inicio, 1), fim


def rotulo(ano: int, mes_inicio: int, mes_fim: int) -> str:
    if mes_inicio == 1 and mes_fim == 12:
        return str(ano)
    if mes_inicio == mes_fim:
        return f"{NOMES_MES[mes_inicio - 1]} de {ano}"
    return f"{NOMES_MES[mes_inicio - 1]} a {NOMES_MES[mes_fim - 1]} de {ano}"
