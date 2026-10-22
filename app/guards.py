"""Validação de entrada e recusas determinísticas (executadas antes de qualquer LLM)."""
import re

from app.texto import normalizar

MAX_PERGUNTA = 1000


def validar_pergunta(texto: str) -> str:
    """Normaliza e valida a pergunta (FR-027). Levanta ValueError com mensagem para o usuário."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("A pergunta não pode ser vazia.")
    if len(texto) > MAX_PERGUNTA:
        raise ValueError(f"A pergunta excede {MAX_PERGUNTA} caracteres.")
    if not any(c.isalnum() for c in texto):
        raise ValueError("A pergunta deve conter texto.")
    return texto


def recusa(pergunta: str) -> str | None:
    """Mensagem de recusa para pedidos indevidos, ou None. Regras entram na Fase 4 (AV-T010)."""
    return None


# Padrões de prompt injection (camada complementar e contornável; FR-029). Casam texto normalizado.
_INJECAO = [re.compile(p, re.M) for p in (
    r"\b(ignor[ae]r?|desconsider[ae]r?|esquec[ae]r?|esqueca)\b.{0,40}\b(instruc|regra|orientac|comando|prompt)",
    r"\b(ignore|disregard|forget)\b.{0,40}\b(instruction|rule|prompt|previous)",
    r"\b(prompt|instrucoes) (do|de) sistema\b|\bsystem prompt\b",
    r"\b(revele|mostre|repita|informe)\b.{0,20}\b(suas|as|seu|o)\b.{0,10}\b(instrucoes|regras|prompt)",
    r"\breveal\b.{0,20}\b(instructions|prompt)",
    r"\bvoce agora e\b|\baja como\b|\bfinja (ser|que)\b|\bmodo (desenvolvedor|dev)\b|\bdeveloper mode\b",
    r"\byou are now\b|\bact as\b|\bpretend (to be|you)\b|\bjailbreak\b|\bdan\b",
    r"^\s*(system|assistant|sistema|assistente)\s*:",
    r"<\|[^|]{0,30}\|>",
)]


def detectar_injecao(texto: str) -> bool:
    """True se o texto parece conter instrução dirigida ao modelo (prompt injection)."""
    norm = normalizar(texto)
    return any(p.search(norm) for p in _INJECAO)
