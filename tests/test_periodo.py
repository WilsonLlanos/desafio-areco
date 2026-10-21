from datetime import date

import pytest

from app.llm.rules import normalizar
from app.periodo import extrair_periodo, intervalo, rotulo


@pytest.mark.parametrize("texto,esperado", [
    ("de janeiro a março de 2025", {"ano": 2025, "mes_inicio": 1, "mes_fim": 3}),
    ("em janeiro de 2026", {"ano": 2026, "mes_inicio": 1, "mes_fim": 1}),
    ("durante 2025", {"ano": 2025}),
    ("no 2º trimestre de 2025", {"ano": 2025, "mes_inicio": 4, "mes_fim": 6}),
    ("primeiro semestre de 2026", {"ano": 2026, "mes_inicio": 1, "mes_fim": 6}),
    ("quanto gastamos em março?", {"mes_inicio": 3, "mes_fim": 3}),
    ("quanto gastamos?", {}),
])
def test_extrair_periodo(texto, esperado):
    assert extrair_periodo(normalizar(texto)) == esperado


def test_intervalo_e_rotulo():
    assert intervalo(2025, 1, 3) == (date(2025, 1, 1), date(2025, 4, 1))
    assert intervalo(2025, 12, 12) == (date(2025, 12, 1), date(2026, 1, 1))
    assert rotulo(2025, 1, 12) == "2025"
    assert rotulo(2026, 1, 1) == "janeiro de 2026"
    assert rotulo(2025, 1, 3) == "janeiro a março de 2025"
