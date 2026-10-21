import shutil
from decimal import Decimal

import psycopg
import pytest

from app import ingestion
from app.config import ROOT
from app.db import connect_owner, connect_ro

DATA = ROOT / "data"


def test_parsers_contagens_e_decimal():
    fin = ingestion.carregar_lancamentos(DATA)
    assert len(fin) == 300
    assert len(ingestion.carregar_orcamento(DATA)) == 144
    assert len(ingestion.carregar_manifestacoes(DATA)) == 180
    assert all(isinstance(r[9], Decimal) for r in fin)  # valor_brl nunca é float


def test_enum_invalido_aborta_com_arquivo_e_linha(tmp_path):
    shutil.copytree(DATA, tmp_path / "data")
    arq = tmp_path / "data" / "ouvidoria" / "manifestacoes.csv"
    arq.write_text(arq.read_text(encoding="utf-8-sig").replace(",Aberto,", ",Inexistente,", 1),
                   encoding="utf-8-sig")
    with pytest.raises(ingestion.IngestionError, match=r"manifestacoes.csv, linha \d+: status fora do enum"):
        ingestion.carregar_manifestacoes(tmp_path / "data")


def test_valor_invalido_aborta(tmp_path):
    shutil.copytree(DATA, tmp_path / "data")
    arq = tmp_path / "data" / "financeiro" / "lancamentos_financeiros.csv"
    arq.write_text(arq.read_text(encoding="utf-8-sig").replace("16360.63", "abc", 1), encoding="utf-8-sig")
    with pytest.raises(ingestion.IngestionError, match="valor_brl inválido"):
        ingestion.carregar_lancamentos(tmp_path / "data")


def _contagens(conn):
    return {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ingestion.TABELAS}


def test_ingestao_idempotente(db_settings):
    primeira = ingestion.ingerir(db_settings)
    segunda = ingestion.ingerir(db_settings)
    assert primeira == segunda == {"lancamentos_financeiros": 300, "orcamento_mensal": 144,
                                   "manifestacoes_ouvidoria": 180}


def test_valor_armazenado_como_numeric(db_settings):
    with connect_ro(db_settings) as conn:
        v = conn.execute("SELECT valor_brl FROM lancamentos_financeiros WHERE id_lancamento='FIN-0001'").fetchone()
    assert v["valor_brl"] == Decimal("16360.63")


def test_papel_ro_le_mas_nao_escreve(db_settings):
    with connect_ro(db_settings) as conn:
        assert conn.execute("SELECT count(*) AS n FROM manifestacoes_ouvidoria").fetchone()["n"] == 180
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("DELETE FROM manifestacoes_ouvidoria")
    with connect_owner(db_settings) as conn:
        assert _contagens(conn)["manifestacoes_ouvidoria"] == 180
