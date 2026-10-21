"""Consultas financeiras pré-definidas e parametrizadas. O LLM só fornece parâmetros validados.

Nomes de coluna vêm de whitelist; valores sempre por %s. Valores monetários em NUMERIC/Decimal.
"""
import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

COLUNA_DATA = {"competencia": "data_competencia", "vencimento": "data_vencimento"}
CONSULTAS = ("soma_despesas", "soma_receitas", "receita_liquida", "comparar_periodos",
             "orcamento_por_departamento", "execucao_orcamentaria", "inadimplencia")
CC_RE = re.compile(r"^CC[1-6]00$")
LIMITE_IDS = 10


class ParamsFinanceiro(BaseModel):
    """Parâmetros extraídos da pergunta. Campo desconhecido ou fora do enum é rejeitado."""
    model_config = ConfigDict(extra="forbid")

    consulta: Literal[CONSULTAS] | None = None
    ano: int | None = None
    mes_inicio: int | None = Field(default=None, ge=1, le=12)
    mes_fim: int | None = Field(default=None, ge=1, le=12)
    tipo_data: Literal["competencia", "vencimento"] | None = None
    criterio_gasto: Literal["paga", "incorrida"] | None = None
    departamento: str | None = None
    centro_custo: str | None = Field(default=None, pattern=CC_RE.pattern)
    categoria: str | None = None
    metrica: Literal["receitas", "despesas"] | None = None  # comparar_periodos
    ano_b: int | None = None
    mes_inicio_b: int | None = Field(default=None, ge=1, le=12)
    mes_fim_b: int | None = Field(default=None, ge=1, le=12)
    ordem: Literal["maior", "menor"] | None = None  # orcamento_por_departamento


def _filtros(inicio: date, fim: date, tipo_data: str, departamento, centro_custo, categoria):
    col = COLUNA_DATA[tipo_data]  # whitelist
    where, args = [f"{col} >= %s", f"{col} < %s"], [inicio, fim]
    for campo, valor in (("departamento", departamento), ("centro_custo", centro_custo),
                         ("categoria", categoria)):
        if valor:
            where.append(f"{campo} = %s")
            args.append(valor)
    return where, args


def somar_lancamentos(conn, *, tipo: Literal["Receita", "Despesa"], status: str | None,
                      tipo_data: str, inicio: date, fim: date, departamento=None,
                      centro_custo=None, categoria=None) -> dict:
    """Total, quantidade e até 10 IDs dos lançamentos do tipo/status no período."""
    where, args = _filtros(inicio, fim, tipo_data, departamento, centro_custo, categoria)
    where.insert(0, "tipo = %s")
    args.insert(0, tipo)
    if status:
        where.append("status = %s")
        args.append(status)
    cond = " AND ".join(where)
    r = conn.execute(f"SELECT COALESCE(SUM(valor_brl), 0) AS total, COUNT(*) AS n "
                     f"FROM lancamentos_financeiros WHERE {cond}", args).fetchone()
    ids = conn.execute(f"SELECT id_lancamento FROM lancamentos_financeiros WHERE {cond} "
                       f"ORDER BY id_lancamento LIMIT {LIMITE_IDS}", args).fetchall()
    return {"total": Decimal(r["total"]), "n": r["n"], "ids": [i["id_lancamento"] for i in ids]}


def orcamento_total(conn, *, ano: int, mes_inicio: int, mes_fim: int, departamento=None,
                    centro_custo=None) -> Decimal:
    where, args = ["ano = %s", "mes::int BETWEEN %s AND %s"], [ano, mes_inicio, mes_fim]
    if departamento:
        where.append("departamento = %s")
        args.append(departamento)
    if centro_custo:
        where.append("centro_custo = %s")
        args.append(centro_custo)
    r = conn.execute("SELECT COALESCE(SUM(orcamento_brl), 0) AS total FROM orcamento_mensal "
                     "WHERE " + " AND ".join(where), args).fetchone()
    return Decimal(r["total"])


def orcamento_por_departamento(conn, *, ano: int, mes_inicio: int, mes_fim: int,
                               centro_custo=None) -> list[dict]:
    """Orçamento somado por departamento no período, do maior para o menor."""
    where, args = ["ano = %s", "mes::int BETWEEN %s AND %s"], [ano, mes_inicio, mes_fim]
    if centro_custo:
        where.append("centro_custo = %s")
        args.append(centro_custo)
    rows = conn.execute("SELECT departamento, centro_custo, SUM(orcamento_brl) AS total "
                        "FROM orcamento_mensal WHERE " + " AND ".join(where) +
                        " GROUP BY departamento, centro_custo ORDER BY total DESC, departamento",
                        args).fetchall()
    return [{"departamento": r["departamento"], "centro_custo": r["centro_custo"],
             "total": Decimal(r["total"])} for r in rows]


def departamentos(conn) -> list[str]:
    return [r["departamento"] for r in
            conn.execute("SELECT DISTINCT departamento FROM orcamento_mensal ORDER BY 1").fetchall()]
