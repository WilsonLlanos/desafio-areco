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




# Padrões de prompt injection (camada complementar e contornável; FR-029). Casam texto normalizado.
_INJECAO = [re.compile(p, re.M) for p in (
    r"\b(ignor|desconsider|esquec)\w*\s+(?:(?:todas?|tod[oa]s|as|os|suas|seus|tuas|essas|estas|quaisquer)\s+){0,3}"
    r"(instrucoes|orientacoes|regras|comandos|diretrizes|restricoes|prompt)\b.{0,15}"
    r"\b(anteriores|acima|previas|iniciais|originais|do sistema|recebidas|que (voce )?recebeu)\b",
    r"\b(ignor|desconsider|esquec)\w*\s+(?:todas\s+)?(suas|seus|tuas|teus)\s+"
    r"(instrucoes|orientacoes|regras|comandos|diretrizes|restricoes)",
    r"\b(ignor|desconsider|esquec)\w*\s+tudo\b.{0,30}\b(acima|anterior|dito|disse)",
    r"\b(ignore|disregard|forget)\b.{0,40}\b(instruction|rule|prompt|previous)",
    r"\b(prompt|instrucoes) (do|de) sistema\b|\bsystem prompt\b",
    r"\b(revele|mostre|repita|informe|liste|diga|escreva|copie)\b.{0,20}\b(suas|seus|seu|tuas|teus|teu)\b.{0,10}"
    r"\b(instrucoes|regras|prompt|configurac|diretrizes)",
    r"\b(repita|mostre|copie)\s+(tudo|todo o texto|o texto)\s+(acima|anterior)",
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


MSG_ESCOPO = ("Só posso ajudar com três assuntos: financeiro (lançamentos e orçamento), informações "
              "internas (políticas e procedimentos) e ouvidoria (protocolos e manifestações). "
              "Reformule a pergunta dentro de um desses temas.")

# Pedido de credencial alheia ou de revelação de credencial (AV-T010, FR-028). "Como troco minha
# senha?" não casa: precisa de um terceiro ou de um pedido para revelar/descobrir.
_CREDENCIAL = r"(senhas?|tokens?|credenciais|credencial|chaves? de api|codigos? (mfa|2fa|de verificacao))"
_TERCEIRO = (r"(outr[oa]s?|colegas?|colaborador(a|es)?|funcionari[oa]s?|gestor(a)?|chefe|diretor(a)?|"
             r"administrador|admin|dele|dela|alguem|usuarios?|pessoas?|clientes?)")
_PEDIDO_CREDENCIAL = [re.compile(p) for p in (
    _CREDENCIAL + r"\b.{0,30}\b(de|do|da|dos|das)\s+(?:(?:meu|minha|um|uma|outro|outra|algum|alguma)\s+)?" + _TERCEIRO + r"\b",
    r"\b(diga|passe|informe|mostre|envie|revele)\s+(a|o|as|os|sua|seu|suas|seus)\s+" + _CREDENCIAL,
    r"\b(descobrir|descubra|quebrar|hackear|invadir)\b.{0,25}\b" + _CREDENCIAL,
    r"\bqual (e )?(a |o )?" + _CREDENCIAL + r"\b",
)]
# Dados pessoais de terceiros (09_politica_privacidade.md). Perguntas sobre a política em si não casam.
TERCEIROS = re.compile(
    r"\b(dados|telefone|endereco|cpf|e-?mail|salario|ferias|saldo|holerite|contato)\b.{0,40}"
    r"\b(de|do|da|dos|das)\s+(?:(?:meu|minha|meus|minhas|um|uma|outro|outra)\s+)?"
    r"(outr[oa]s?|colegas?|colaborador(a|es)?|funcionari[oa]s?|clientes?)\b")

MSG_CREDENCIAL = (
    "Não posso informar senhas, tokens ou credenciais, nem dados pessoais de outras pessoas. Senhas e "
    "tokens nunca devem ser compartilhados (04_seguranca_da_informacao.md). Para acesso a sistemas, abra "
    "chamado no portal de TI; suspeitas de incidente vão para seguranca@aurora.example; solicitações "
    "sobre dados pessoais vão para privacidade@aurora.example (09_politica_privacidade.md).")
FONTES_CREDENCIAL = ["04_seguranca_da_informacao.md", "09_politica_privacidade.md"]
MSG_TERCEIROS = ("Não posso revelar dados de outros colaboradores ou de clientes. Solicitações sobre dados "
                 "pessoais devem ser encaminhadas ao canal privacidade@aurora.example.")
FONTE_TERCEIROS = "09_politica_privacidade.md"
MSG_INJECAO = ("Não posso seguir instruções que tentem mudar meu funcionamento ou revelar minhas "
               "instruções. " + MSG_ESCOPO)


def recusa(pergunta: str) -> tuple[str, list[str]] | None:
    """(mensagem, arquivos-fonte) para pedidos indevidos, ou None. Roda antes de qualquer LLM."""
    norm = normalizar(pergunta)
    if detectar_injecao(pergunta):  # injeção direta (FR-029)
        return MSG_INJECAO, []
    if any(p.search(norm) for p in _PEDIDO_CREDENCIAL):
        return MSG_CREDENCIAL, FONTES_CREDENCIAL
    if TERCEIROS.search(norm):
        return f"{MSG_TERCEIROS} (Fonte: {FONTE_TERCEIROS}.)", [FONTE_TERCEIROS]
    return None
