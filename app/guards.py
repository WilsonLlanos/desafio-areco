"""Validação de entrada e recusas determinísticas (executadas antes de qualquer LLM)."""
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
