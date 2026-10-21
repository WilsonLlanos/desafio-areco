"""Consultas parametrizadas de ouvidoria. O LLM nunca produz SQL (constituição II)."""
import re

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
