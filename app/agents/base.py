"""Tipos e formatação compartilhados pelos agentes."""
from dataclasses import dataclass, field
from decimal import Decimal

from app.api.schemas import Fonte


@dataclass
class Resultado:
    resposta: str
    status: str
    fontes: list[Fonte] = field(default_factory=list)
    dados: dict = field(default_factory=dict)  # valores calculados; usados em testes, não vão à API


def brl(valor: Decimal) -> str:
    """Decimal → 'R$ 1.234,56' (sem float)."""
    inteiro = f"{valor.quantize(Decimal('0.01')):,.2f}"
    return "R$ " + inteiro.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(parte: Decimal, total: Decimal) -> str:
    return f"{(parte / total * 100).quantize(Decimal('0.01'))}".replace(".", ",") + "%"


def esclarecimento(texto: str) -> Resultado:
    return Resultado(texto, "esclarecimento")
