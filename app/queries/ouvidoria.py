"""Consultas parametrizadas de ouvidoria. O LLM nunca produz SQL (constituição II)."""
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

PROTOCOLO_RE = re.compile(r"^OUV-\d{4}$")

_BUSCAR_PROTOCOLO = """
SELECT protocolo, data_abertura, categoria, assunto, canal_entrada, prioridade, status,
       area_responsavel, data_resposta, prazo_referencia_dias
FROM manifestacoes_ouvidoria WHERE protocolo = %s
"""


def protocolo_valido(valor: str | None) -> bool:
    return bool(valor and PROTOCOLO_RE.match(valor))


def buscar_protocolo(conn, protocolo: str) -> dict | None:
    if not protocolo_valido(protocolo):
        raise ValueError(f"protocolo inválido: {protocolo!r}")
    return conn.execute(_BUSCAR_PROTOCOLO, (protocolo,)).fetchone()


# --- Filtros, contagens, listas e referência (Fase 2) -------------------------------------------
CANAIS = ["Portal", "E-mail", "Telefone", "Chat"]
COLUNAS_FILTRO = {"status": "status", "categoria": "categoria", "prioridade": "prioridade",
                  "canal": "canal_entrada"}  # whitelist de colunas
LIMITE_LISTA = 10


@lru_cache(maxsize=4)
def carregar_referencia(data_dir: Path) -> dict:
    """Valores enumerados válidos, lidos de referencia_ouvidoria.json (+ canais do dicionário de dados)."""
    ref = json.loads((Path(data_dir) / "ouvidoria" / "referencia_ouvidoria.json")
                     .read_text(encoding="utf-8-sig"))
    return {"status": ref["status_validos"], "prioridade": ref["prioridades_validas"],
            "categoria": ref["categorias"], "canal": CANAIS}


def _where(filtros: dict, data_de: date | None, data_ate: date | None):
    where, args = [], []
    for chave, coluna in COLUNAS_FILTRO.items():
        if filtros.get(chave):
            where.append(f"{coluna} = %s")
            args.append(filtros[chave])
    if data_de:
        where.append("data_abertura >= %s")
        args.append(data_de)
    if data_ate:
        where.append("data_abertura < %s")  # limite superior exclusivo
        args.append(data_ate)
    return (" WHERE " + " AND ".join(where)) if where else "", args


def contar(conn, filtros: dict, data_de: date | None = None, data_ate: date | None = None) -> int:
    cond, args = _where(filtros, data_de, data_ate)
    return conn.execute(f"SELECT count(*) AS n FROM manifestacoes_ouvidoria{cond}", args).fetchone()["n"]


def listar(conn, filtros: dict, data_de: date | None = None, data_ate: date | None = None) -> list[dict]:
    """Até LIMITE_LISTA manifestações, em ordem determinística (data de abertura, protocolo)."""
    cond, args = _where(filtros, data_de, data_ate)
    return conn.execute(
        "SELECT protocolo, data_abertura, categoria, assunto, canal_entrada, prioridade, status "
        f"FROM manifestacoes_ouvidoria{cond} ORDER BY data_abertura, protocolo LIMIT {LIMITE_LISTA}",
        args).fetchall()
