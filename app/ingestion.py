"""Carga idempotente dos CSV no PostgreSQL (FR-020, FR-022).

Valida datas e enums, converte valores monetários para Decimal, faz upsert pela chave primária
e cria o papel somente leitura usado pela API.
"""
import csv
import json
import sys
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from psycopg import sql

from app.config import Settings, load_settings
from app.db import connect_owner

TIPOS = {"Receita", "Despesa"}
STATUS_FIN = {"Pago", "Pendente", "Atrasado"}
CANAIS = {"Portal", "E-mail", "Telefone", "Chat"}
TABELAS = ("lancamentos_financeiros", "orcamento_mensal", "manifestacoes_ouvidoria")


class IngestionError(Exception):
    def __init__(self, arquivo: str, linha: int, mensagem: str):
        super().__init__(f"{arquivo}, linha {linha}: {mensagem}")


def _ler(path: Path) -> list[tuple[int, dict]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [(i, row) for i, row in enumerate(csv.DictReader(f), start=2)]


def _data(valor: str, arq: str, linha: int, campo: str, obrigatoria: bool = True):
    if not valor:
        if obrigatoria:
            raise IngestionError(arq, linha, f"{campo} vazio")
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise IngestionError(arq, linha, f"{campo} inválido: {valor!r}") from None


def _decimal(valor: str, arq: str, linha: int, campo: str) -> Decimal:
    try:
        d = Decimal(valor)
    except InvalidOperation:
        raise IngestionError(arq, linha, f"{campo} inválido: {valor!r}") from None
    if d < 0:
        raise IngestionError(arq, linha, f"{campo} negativo: {valor!r}")
    return d


def _enum(valor: str, validos, arq: str, linha: int, campo: str) -> str:
    if valor not in validos:
        raise IngestionError(arq, linha, f"{campo} fora do enum: {valor!r}")
    return valor


def carregar_lancamentos(data_dir: Path) -> list[tuple]:
    arq = "lancamentos_financeiros.csv"
    out = []
    for n, r in _ler(data_dir / "financeiro" / arq):
        out.append((
            r["id_lancamento"],
            _data(r["data_competencia"], arq, n, "data_competencia"),
            _data(r["data_vencimento"], arq, n, "data_vencimento"),
            _enum(r["tipo"], TIPOS, arq, n, "tipo"),
            r["categoria"], r["descricao"], r["centro_custo"], r["departamento"], r["contraparte"],
            _decimal(r["valor_brl"], arq, n, "valor_brl"),
            _enum(r["status"], STATUS_FIN, arq, n, "status"),
            r["metodo_pagamento"] or None, r["observacao"] or None,
        ))
    return out


def carregar_orcamento(data_dir: Path) -> list[tuple]:
    arq = "orcamento_mensal.csv"
    out = []
    for n, r in _ler(data_dir / "financeiro" / arq):
        if not r["mes"].isdigit() or not 1 <= int(r["mes"]) <= 12:
            raise IngestionError(arq, n, f"mes inválido: {r['mes']!r}")
        out.append((
            int(r["ano"]), r["mes"].zfill(2), r["centro_custo"], r["departamento"],
            _decimal(r["orcamento_brl"], arq, n, "orcamento_brl"),
            r["versao_orcamento"], r["observacao"] or None,
        ))
    return out


def carregar_manifestacoes(data_dir: Path) -> list[tuple]:
    arq = "manifestacoes.csv"
    ref = json.loads((data_dir / "ouvidoria" / "referencia_ouvidoria.json").read_text(encoding="utf-8-sig"))
    status, prios, cats = set(ref["status_validos"]), set(ref["prioridades_validas"]), set(ref["categorias"])
    out = []
    for n, r in _ler(data_dir / "ouvidoria" / arq):
        out.append((
            r["protocolo"],
            _data(r["data_abertura"], arq, n, "data_abertura"),
            _enum(r["categoria"], cats, arq, n, "categoria"),
            r["assunto"],
            _enum(r["canal_entrada"], CANAIS, arq, n, "canal_entrada"),
            _enum(r["prioridade"], prios, arq, n, "prioridade"),
            _enum(r["status"], status, arq, n, "status"),
            r["area_responsavel"], r["resumo_manifestacao"],
            _data(r["data_resposta"], arq, n, "data_resposta", obrigatoria=False),
            r["resposta_resumo"] or None,
            int(r["prazo_referencia_dias"]),
            r["dados_pessoais"] or None, r["observacao"] or None,
        ))
    return out


UPSERT_FIN = """
INSERT INTO lancamentos_financeiros (id_lancamento, data_competencia, data_vencimento, tipo, categoria,
  descricao, centro_custo, departamento, contraparte, valor_brl, status, metodo_pagamento, observacao)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (id_lancamento) DO UPDATE SET data_competencia=EXCLUDED.data_competencia,
  data_vencimento=EXCLUDED.data_vencimento, tipo=EXCLUDED.tipo, categoria=EXCLUDED.categoria,
  descricao=EXCLUDED.descricao, centro_custo=EXCLUDED.centro_custo, departamento=EXCLUDED.departamento,
  contraparte=EXCLUDED.contraparte, valor_brl=EXCLUDED.valor_brl, status=EXCLUDED.status,
  metodo_pagamento=EXCLUDED.metodo_pagamento, observacao=EXCLUDED.observacao
"""

UPSERT_ORC = """
INSERT INTO orcamento_mensal (ano, mes, centro_custo, departamento, orcamento_brl, versao_orcamento, observacao)
VALUES (%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (ano, mes, centro_custo) DO UPDATE SET departamento=EXCLUDED.departamento,
  orcamento_brl=EXCLUDED.orcamento_brl, versao_orcamento=EXCLUDED.versao_orcamento,
  observacao=EXCLUDED.observacao
"""

UPSERT_OUV = """
INSERT INTO manifestacoes_ouvidoria (protocolo, data_abertura, categoria, assunto, canal_entrada,
  prioridade, status, area_responsavel, resumo_manifestacao, data_resposta, resposta_resumo,
  prazo_referencia_dias, dados_pessoais, observacao)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (protocolo) DO UPDATE SET data_abertura=EXCLUDED.data_abertura,
  categoria=EXCLUDED.categoria, assunto=EXCLUDED.assunto, canal_entrada=EXCLUDED.canal_entrada,
  prioridade=EXCLUDED.prioridade, status=EXCLUDED.status, area_responsavel=EXCLUDED.area_responsavel,
  resumo_manifestacao=EXCLUDED.resumo_manifestacao, data_resposta=EXCLUDED.data_resposta,
  resposta_resumo=EXCLUDED.resposta_resumo, prazo_referencia_dias=EXCLUDED.prazo_referencia_dias,
  dados_pessoais=EXCLUDED.dados_pessoais, observacao=EXCLUDED.observacao
"""


def criar_papel_ro(conn: psycopg.Connection, settings: Settings) -> None:
    """Cria (ou atualiza a senha do) papel somente leitura e concede SELECT nas 3 tabelas."""
    papel = sql.Identifier(settings.db_ro_user)
    existe = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (settings.db_ro_user,)).fetchone()
    # Comandos utilitários não aceitam parâmetros: senha vai como literal escapado.
    verbo = "ALTER" if existe else "CREATE"
    conn.execute(sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(
        sql.SQL(verbo), papel, sql.Literal(settings.db_ro_password)))
    conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
        sql.Identifier(settings.db_name), papel))
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(papel))
    for t in TABELAS:
        conn.execute(sql.SQL("GRANT SELECT ON {} TO {}").format(sql.Identifier(t), papel))


def ingerir(settings: Settings) -> dict[str, int]:
    """Aplica o schema, carrega as bases e prepara o papel ro. Valida tudo antes de gravar."""
    fin = carregar_lancamentos(settings.data_dir)
    orc = carregar_orcamento(settings.data_dir)
    ouv = carregar_manifestacoes(settings.data_dir)
    schema = (settings.data_dir / "sql" / "schema.sql").read_text(encoding="utf-8")
    with connect_owner(settings) as conn:
        conn.execute(schema)
        with conn.cursor() as cur:
            cur.executemany(UPSERT_FIN, fin)
            cur.executemany(UPSERT_ORC, orc)
            cur.executemany(UPSERT_OUV, ouv)
        criar_papel_ro(conn, settings)
        conn.commit()
        return {t: conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(t))).fetchone()[0]
                for t in TABELAS}


def main() -> int:
    settings = load_settings()
    for tentativa in range(1, 31):  # o banco pode ainda estar subindo
        try:
            contagens = ingerir(settings)
            break
        except psycopg.OperationalError as e:
            print(f"banco indisponível ({tentativa}/30): {e}", file=sys.stderr)
            time.sleep(2)
        except IngestionError as e:
            print(f"ERRO de ingestão: {e}", file=sys.stderr)
            return 1
    else:
        print("ERRO: banco não respondeu", file=sys.stderr)
        return 1
    print("ingestão concluída:", contagens)
    return 0


if __name__ == "__main__":
    sys.exit(main())
