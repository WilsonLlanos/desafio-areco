"""Avaliação AV-T001–AV-T012 contra a API em execução, com LLM real (FR-031, US5).

Aprovado/reprovado = checagens determinísticas (domínio, fonte esperada, conteúdo-chave do critério e,
nos casos financeiros, valor do oráculo calculado direto dos CSV). Resposta em modo degradado (regras,
por falha do provedor) é repetida até 2 vezes; se continuar degradada, o caso fica `nao_avaliado_llm`.
O juiz (scripts/judge.py) é complementar e só roda com JUDGE_MODEL.

Uso (no contêiner, gravando em docs/evaluation do host):
  docker compose run --rm -v "$PWD/docs/evaluation:/app/docs/evaluation" app \
      python scripts/evaluate.py --url http://app:8000
"""
import argparse
import json
import math
import os
import sys
import time
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.judge import Juiz, divergente  # noqa: E402
from tests import oracle  # noqa: E402

CASOS = ROOT / "data" / "testes" / "perguntas_avaliacao.json"
DOCS = ROOT / "data" / "informacoes_internas"
REPETICOES = 2
ESPERA_S = 3


def norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def brl(valor: Decimal) -> str:
    s = f"{valor.quantize(Decimal('0.01')):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


# --- referências (oráculo e documentos), usadas nas checagens e pelo juiz ---------------------------
def _oraculo() -> dict:
    t006, n006 = oracle.soma("Despesa", 2025, 1, 3, status="Pago")
    t011, n011 = oracle.soma("Receita", 2025)
    jan26 = oracle.orcamento_por_departamento(2026, 1)
    dep = max(jan26, key=jan26.get)
    ouv2 = next(r for r in oracle.OUV if r["protocolo"] == "OUV-0002")
    status = json.loads((ROOT / "data/ouvidoria/referencia_ouvidoria.json").read_text(encoding="utf-8-sig"))["status_validos"]
    return {"T006": (t006, n006), "T011": (t011, n011), "T007": (dep, jan26[dep], jan26), "OUV-0002": ouv2,
            "status": status}


def referencia(caso: dict, o: dict) -> str:
    cid = caso["id"]
    if cid == "T006":
        return f"Despesas com status Pago e competência de janeiro a março de 2025: {brl(o['T006'][0])} ({o['T006'][1]} lançamentos)."
    if cid == "T011":
        return f"Receitas com competência em 2025 (todos os status): {brl(o['T011'][0])} ({o['T011'][1]} lançamentos)."
    if cid == "T007":
        dep, valor, todos = o["T007"]
        return f"Maior orçamento em janeiro de 2026: {dep} ({brl(valor)}). Todos: " + \
            "; ".join(f"{d}: {brl(v)}" for d, v in sorted(todos.items(), key=lambda x: -x[1]))
    if cid == "T004":
        return "O protocolo OUV-9999 não existe em manifestacoes.csv."
    if cid == "T005":
        return "Status válidos: " + ", ".join(o["status"])
    if cid == "T009":
        return json.dumps(o["OUV-0002"], ensure_ascii=False)
    arquivos = [a.strip() for a in caso["fonte_esperada"].split(";")]
    return "\n\n".join((DOCS / a).read_text(encoding="utf-8-sig") for a in arquivos if (DOCS / a).exists())


def _tem(resposta: str, *termos: str) -> list[str]:
    r = norm(resposta)
    return [t for t in termos if norm(t) not in r]


def checar(caso: dict, d: dict, o: dict) -> tuple[bool, list[str]]:
    """Checagens determinísticas; devolve (aprovado, motivos de reprovação)."""
    cid, resp = caso["id"], d.get("resposta", "")
    fontes = [f["ref"] for f in d.get("fontes", [])]
    motivos = []
    if cid == "T010":
        if d.get("status") != "recusado":
            motivos.append(f"esperava recusa, veio status {d.get('status')}")
    elif d.get("dominio") != caso["dominio_esperado"]:
        motivos.append(f"domínio {d.get('dominio')} ≠ {caso['dominio_esperado']}")
    for f in (a.strip() for a in caso["fonte_esperada"].split(";")):
        if f not in fontes:
            motivos.append(f"fonte {f} ausente")
    faltando = {
        "T001": _tem(resp, "portal", "30 dias"),
        "T002": _tem(resp, "10 dias", "comprovante"),
        "T003": _tem(resp, "liderança", "gerente", "diretoria"),
        "T004": _tem(resp, "OUV-9999", "não foi encontrado"),
        "T005": _tem(resp, *o["status"]),
        "T006": _tem(resp, brl(o["T006"][0])),
        "T007": _tem(resp, o["T007"][0], brl(o["T007"][1])),
        "T008": _tem(resp, "imediatamente", "seguranca@aurora.example"),
        "T009": _tem(resp, "Aguardando área responsável"),
        "T010": _tem(resp, "senha"),
        "T011": _tem(resp, brl(o["T011"][0])),
        "T012": _tem(resp, "imediatamente", "senhas"),
    }[cid]
    motivos += [f"falta \"{t}\"" for t in faltando]
    if cid == "T004" and d.get("status") != "nao_encontrado":
        motivos.append("protocolo inexistente deveria ser nao_encontrado")
    return not motivos, motivos


def p90(valores: list[int]) -> int | None:
    if not valores:
        return None
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(0.9 * len(ordenados)) - 1)]


def perguntar(cliente: httpx.Client, pergunta: str) -> tuple[dict, int]:
    """Repete enquanto a resposta vier degradada (até REPETICOES vezes)."""
    for tentativa in range(1, REPETICOES + 2):
        d = cliente.post("/ask", json={"pergunta": pergunta}).json()
        if d.get("modo") != "degradado" or tentativa == REPETICOES + 1:
            return d, tentativa
        time.sleep(ESPERA_S)
    raise AssertionError("inalcançável")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("EVAL_URL", "http://localhost:8000"))
    ap.add_argument("--saida", default=str(ROOT / "docs" / "evaluation"))
    args = ap.parse_args()

    casos = json.loads(CASOS.read_text(encoding="utf-8-sig"))["casos"]
    o = _oraculo()
    modelo_juiz = os.environ.get("JUDGE_MODEL", "").strip()
    juiz = Juiz.gemini(os.environ["GEMINI_API_KEY"], modelo_juiz) if modelo_juiz and os.environ.get("GEMINI_API_KEY") else None
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    arq = saida / f"avaliacao-{carimbo}.jsonl"

    registros, interacoes = [], []
    with httpx.Client(base_url=args.url, timeout=60) as cliente:
        modo_api = cliente.get("/health").json().get("modo")
        if modo_api != "llm":
            print("AVISO: a API está sem chave (modo degradado); nenhum caso será avaliado com LLM.")
        for caso in casos:
            d, tentativas = perguntar(cliente, caso["pergunta"])
            aprovado, motivos = checar(caso, d, o)
            modo = d.get("modo")
            resultado = "nao_avaliado_llm" if modo == "degradado" else ("pass" if aprovado else "fail")
            fontes = [f["ref"] for f in d.get("fontes", [])]
            j = juiz.avaliar(caso, d.get("resposta", ""), fontes, referencia(caso, o)) if juiz else "nao_executado"
            registros.append({
                "caso_id": f"AV-{caso['id']}", "trace_id": d.get("trace_id"), "pergunta": caso["pergunta"],
                "dominio_esperado": caso["dominio_esperado"], "dominio_obtido": d.get("dominio"),
                "fonte_esperada": caso["fonte_esperada"], "fonte_obtida": fontes[:12], "criterio": caso["criterio"],
                "status": d.get("status"), "resultado": resultado, "checagens_ok": aprovado, "motivos": motivos,
                "modo": modo, "tentativas": tentativas, "latencia_ms": d.get("latencia_ms"),
                "juiz_modelo": modelo_juiz or None, "juiz": j,
                "divergente": divergente(aprovado if resultado != "nao_avaliado_llm" else None, j),
                "resposta": d.get("resposta", "")[:600]})
            r = cliente.get(f"/traces/{d.get('trace_id')}")
            if r.status_code == 200:
                interacoes.append(r.json())

    lat_todas = [r["latencia_ms"] for r in registros if r["latencia_ms"] is not None]
    lat_llm = [r["latencia_ms"] for r in registros if r["modo"] == "llm" and r["latencia_ms"] is not None]
    resumo = {
        "resumo": True, "timestamp": datetime.now(timezone.utc).isoformat(), "modo_api": modo_api,
        "total": len(registros),
        "aprovados_llm": sum(r["resultado"] == "pass" for r in registros),
        "reprovados_llm": sum(r["resultado"] == "fail" for r in registros),
        "nao_avaliados_llm": sum(r["resultado"] == "nao_avaliado_llm" for r in registros),
        "aprovados_em_modo_degradado": sum(r["resultado"] == "nao_avaliado_llm" and r["checagens_ok"] for r in registros),
        "p90_latencia_ms_total": p90(lat_todas), "p90_latencia_ms_llm": p90(lat_llm), "meta_p90_ms": 10000,
        "juiz_modelo": modelo_juiz or None,
        "juiz_erros": sum(r["juiz"] == "erro" for r in registros),
        "divergencias": sum(bool(r["divergente"]) for r in registros),
    }
    with arq.open("w", encoding="utf-8") as f:
        for r in registros + [resumo]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (saida / "interacoes-amostra.jsonl").open("w", encoding="utf-8") as f:
        for r in interacoes:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"{'caso':8} {'resultado':17} {'modo':10} {'tent':>4} {'ms':>6}  juiz        motivos")
    for r in registros:
        jz = r["juiz"] if isinstance(r["juiz"], str) else ("atende" if r["juiz"]["atende_criterio"] else "NÃO atende")
        div = " (DIVERGENTE)" if r["divergente"] else ""
        print(f"{r['caso_id']:8} {r['resultado']:17} {r['modo'] or '-':10} {r['tentativas']:>4} "
              f"{r['latencia_ms'] or 0:>6}  {jz}{div}  {'; '.join(r['motivos'])}")
    print(json.dumps({k: v for k, v in resumo.items() if k not in ("resumo", "timestamp")}, ensure_ascii=False))
    print(f"log: {arq}")
    return 0 if resumo["reprovados_llm"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
