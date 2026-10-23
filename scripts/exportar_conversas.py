"""Exporta as sessões do Claude Code (JSONL) para Markdown sanitizado em docs/conversas/ (T065).

Mantém: mensagens do usuário, texto da IA, uma linha por chamada de ferramenta, perguntas de decisão
(AskUserQuestion) com as respostas e o plano aprovado (ExitPlanMode). Omite: saídas de ferramentas,
blocos de sistema (<system-reminder>), corpo das skills e raciocínio interno.
Sanitiza: e-mails (exceto @aurora.example e noreply@anthropic.com), chaves `AIza…`, valores de
`*PASSWORD=` e o diretório pessoal.

Uso: python scripts/exportar_conversas.py <dir_das_sessoes> <saida> <id>:<arquivo.md>:<título> ...
"""
import json
import re
import sys
from pathlib import Path

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PERMITIDOS = ("@aurora.example", "noreply@anthropic.com")
_SUBST = [
    (re.compile(r"AIza[0-9A-Za-z_-]{20,}"), "[CHAVE REMOVIDA]"),
    (re.compile(r"(PASSWORD[=:]\s*)(?!\[)\S+"), r"\1[REMOVIDO]"),
    (re.compile(r"(PASSWORD:\s*)\S+"), r"\1[REMOVIDO]"),
    (re.compile(r"/home/[^/\s]+"), "~"),
    (re.compile(r'<pasted_content id="[^"]*">'), "_(início do texto colado)_"),
    (re.compile(r'</pasted_content id="[^"]*">|</pasted_content>'), "_(fim do texto colado)_"),
]


def sanitizar(texto: str) -> str:
    texto = _EMAIL.sub(lambda m: m.group(0) if m.group(0).endswith(_PERMITIDOS) else "[E-MAIL REMOVIDO]", texto)
    for rx, novo in _SUBST:
        texto = rx.sub(novo, texto)
    return texto


def _texto_usuario(c: str) -> str | None:
    c = re.sub(r"<system-reminder>.*?</system-reminder>", "", c, flags=re.S)
    if m := re.search(r"<command-name>(.*?)</command-name>", c, re.S):
        args = re.search(r"<command-args>(.*?)</command-args>", c, re.S)
        return f"`{m.group(1).strip()}` {args.group(1).strip() if args else ''}".strip()
    if c.lstrip().startswith("Base directory for this skill:"):
        return None  # corpo da skill: instruções do Spec Kit, não do usuário
    if c.lstrip().startswith("This session is being continued from a previous conversation"):
        return "_(resumo automático do contexto anterior, gerado ao compactar a conversa; omitido)_"
    if "<local-command" in c or "<command-message>" in c:
        return None
    return c.strip() or None


def _ferramenta(b: dict) -> str:
    nome, ent = b["name"], b.get("input", {})
    if nome == "AskUserQuestion":
        qs = "\n".join(f"  - {q['question']} — opções: " + "; ".join(o["label"] for o in q.get("options", []))
                       for q in ent.get("questions", []))
        return f"- **Pergunta ao usuário** (`AskUserQuestion`):\n{qs}"
    if nome == "ExitPlanMode":
        return "- **Plano apresentado para aprovação** (`ExitPlanMode`):\n\n" + \
            "\n".join("  > " + linha for linha in ent.get("plan", "").splitlines())
    detalhe = ent.get("description") or ent.get("file_path") or ent.get("skill") or ent.get("pattern") or ""
    return f"- `{nome}`: {detalhe}".rstrip(": ")


def exportar(jsonl: Path, titulo: str) -> str:
    saida = [f"# {titulo}", "", f"Sessão `{jsonl.stem}` (Claude Code). Carimbos em UTC.", ""]
    perguntas: set[str] = set()
    ultimo = None  # autor do último cabeçalho: mensagens seguidas do mesmo autor ficam juntas

    def bloco(autor: str, quando: str, texto: str):
        nonlocal ultimo
        if autor != ultimo:
            saida.extend([f"### {autor} — {quando}", ""])
            ultimo = autor
        saida.extend([texto, ""])

    for linha in jsonl.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        if r.get("type") not in ("user", "assistant") or r.get("isMeta"):
            continue
        c, quando = r["message"]["content"], (r.get("timestamp") or "")[:16].replace("T", " ")
        if r["type"] == "user":
            if isinstance(c, str):
                if (t := _texto_usuario(c)) is not None:
                    bloco("Usuário", quando, t)
                continue
            for b in c:
                if b.get("type") == "text" and (t := _texto_usuario(b["text"])) is not None:
                    bloco("Usuário", quando, t)
                elif b.get("type") == "tool_result":
                    conteudo = b.get("content")
                    conteudo = conteudo if isinstance(conteudo, str) else " ".join(
                        x.get("text", "") for x in conteudo or [] if isinstance(x, dict))
                    if b.get("tool_use_id") in perguntas:
                        saida += [f"**Resposta do usuário**: {conteudo.strip()}", ""]
                    elif "doesn't want to proceed" in conteudo or "rejected" in conteudo[:200]:
                        saida += ["_(o usuário recusou esta chamada)_", ""]
            continue
        partes = []
        for b in c if isinstance(c, list) else [{"type": "text", "text": c}]:
            if b.get("type") == "text" and b["text"].strip():
                partes.append(b["text"].strip())
            elif b.get("type") == "tool_use":
                if b["name"] == "AskUserQuestion":
                    perguntas.add(b["id"])
                partes.append(_ferramenta(b))
        if partes:
            bloco("Claude", quando, "\n".join(partes))
    return sanitizar("\n".join(saida))


def main() -> int:
    origem, destino = Path(sys.argv[1]).expanduser(), Path(sys.argv[2])
    destino.mkdir(parents=True, exist_ok=True)
    for item in sys.argv[3:]:
        sid, arquivo, titulo = item.split(":", 2)
        texto = exportar(origem / f"{sid}.jsonl", titulo)
        (destino / arquivo).write_text(texto, encoding="utf-8")
        print(f"{arquivo}: {len(texto) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
