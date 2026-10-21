"""Cálculos independentes sobre os CSV de data/ (csv + Decimal), sem usar o código da aplicação."""
import csv
from decimal import Decimal
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def _ler(rel: str) -> list[dict]:
    with (DATA / rel).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


LANC = _ler("financeiro/lancamentos_financeiros.csv")
ORC = _ler("financeiro/orcamento_mensal.csv")
OUV = _ler("ouvidoria/manifestacoes.csv")


def soma(tipo: str, ano: int, mes_ini: int = 1, mes_fim: int = 12, *, status: str | None = None,
         campo: str = "data_competencia", departamento: str | None = None,
         centro_custo: str | None = None) -> tuple[Decimal, int]:
    total, n = Decimal("0"), 0
    for r in LANC:
        a, m = int(r[campo][:4]), int(r[campo][5:7])
        if r["tipo"] != tipo or a != ano or not mes_ini <= m <= mes_fim:
            continue
        if status and r["status"] != status:
            continue
        if departamento and r["departamento"] != departamento:
            continue
        if centro_custo and r["centro_custo"] != centro_custo:
            continue
        total += Decimal(r["valor_brl"])
        n += 1
    return total, n


def orcamento(ano: int, mes_ini: int, mes_fim: int, departamento: str | None = None) -> Decimal:
    return sum((Decimal(r["orcamento_brl"]) for r in ORC
                if int(r["ano"]) == ano and mes_ini <= int(r["mes"]) <= mes_fim
                and (not departamento or r["departamento"] == departamento)), Decimal("0"))


def orcamento_por_departamento(ano: int, mes: int) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for r in ORC:
        if int(r["ano"]) == ano and int(r["mes"]) == mes:
            out[r["departamento"]] = out.get(r["departamento"], Decimal("0")) + Decimal(r["orcamento_brl"])
    return out


def ouvidoria(**filtros) -> list[dict]:
    """Filtros por igualdade (status, categoria, prioridade, canal_entrada) e prefixo de data_abertura."""
    prefixo = filtros.pop("abertura", "")
    return sorted((r for r in OUV if r["data_abertura"].startswith(prefixo)
                   and all(r[k] == v for k, v in filtros.items())),
                  key=lambda r: (r["data_abertura"], r["protocolo"]))
