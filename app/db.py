"""Acesso ao banco. A API usa apenas o papel somente leitura (constituição II)."""
import psycopg
from psycopg.rows import dict_row

from app.config import Settings


def connect_ro(settings: Settings) -> psycopg.Connection:
    return psycopg.connect(**settings.ro_conninfo(), row_factory=dict_row, connect_timeout=5)


def connect_owner(settings: Settings) -> psycopg.Connection:
    return psycopg.connect(**settings.owner_conninfo(), connect_timeout=5)


def ping(settings: Settings) -> bool:
    """True se o banco responde com o papel somente leitura."""
    try:
        with connect_ro(settings) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False
