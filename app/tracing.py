"""Rastreabilidade (constituição I): trace_id por requisição e log estruturado em JSON Lines."""
import json
import logging
import threading
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_lock = threading.Lock()
logger = logging.getLogger("aurora.interactions")

CAMPOS = ("timestamp", "trace_id", "pergunta", "dominio_previsto", "confianca", "agente",
          "fontes", "latencia_ms", "status", "modo", "erro")


def new_trace_id() -> str:
    tid = str(uuid.uuid4())
    _trace_id.set(tid)
    return tid


def current_trace_id() -> str:
    return _trace_id.get()


def record_interaction(log_dir: Path, **dados) -> dict:
    """Grava um registro por requisição, com todos os campos de data-model.md."""
    registro = {c: dados.get(c) for c in CAMPOS}
    registro["timestamp"] = datetime.now(timezone.utc).isoformat()
    registro["trace_id"] = registro["trace_id"] or current_trace_id()
    registro["fontes"] = registro["fontes"] or []
    linha = json.dumps(registro, ensure_ascii=False)
    logger.info(linha)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        with _lock, (log_dir / "interactions.jsonl").open("a", encoding="utf-8") as f:
            f.write(linha + "\n")
    except OSError:
        logger.exception("falha ao gravar interactions.jsonl")  # nunca derruba a requisição
    return registro


def find_trace(log_dir: Path, trace_id: str) -> dict | None:
    arq = log_dir / "interactions.jsonl"
    if not arq.exists():
        return None
    achado = None
    with arq.open(encoding="utf-8") as f:
        for linha in f:
            if trace_id in linha:
                r = json.loads(linha)
                if r.get("trace_id") == trace_id:
                    achado = r
    return achado
