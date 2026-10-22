"""API FastAPI: /ask, /traces/{id}, /health e frontend estático."""
import logging
import time
from contextlib import contextmanager

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db, tracing
from app.api.schemas import AskRequest, AskResponse
from app.config import Settings, load_settings
from app.llm.base import LLMClient
from app.llm.rules import RulesLLM
from app.orchestrator import montar_grafo
from app.rag.index import Indice

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
log = logging.getLogger("aurora")


def create_app(settings: Settings | None = None, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or load_settings()
    indice = Indice(settings.data_dir)
    log.info("índice RAG: %d itens (%d descartados)", len(indice.itens), len(indice.descartados))
    regras = RulesLLM(settings.data_dir, indice)
    if llm is None and settings.gemini_api_key:
        from app.llm.gemini import GeminiLLM
        llm = GeminiLLM(settings.gemini_api_key, settings.gemini_model, settings.data_dir)
    llm = llm or regras
    log.info("LLM: %s", f"Gemini ({settings.gemini_model})" if llm.modo == "llm" else "regras (modo degradado)")
    app = FastAPI(title="Orquestrador Aurora", version="0.1.0")

    @contextmanager
    def conexao():
        with db.connect_ro(settings) as conn:
            yield conn

    grafo = montar_grafo(llm, conexao, settings.confidence_threshold, settings.data_dir, indice,
                         reserva=regras if llm is not regras else None)

    def erro(status: int, detail: str, pergunta: str | None = None, t0: float | None = None,
             exc: Exception | None = None) -> JSONResponse:
        tid = tracing.current_trace_id()
        tracing.record_interaction(
            settings.log_dir, trace_id=tid, pergunta=pergunta, status="erro", modo=llm.modo,
            latencia_ms=int((time.perf_counter() - t0) * 1000) if t0 else 0,
            erro=f"{type(exc).__name__}: {exc}"[:300] if exc else detail)
        return JSONResponse({"trace_id": tid, "detail": detail}, status_code=status,
                            headers={"X-Trace-Id": tid})

    @app.middleware("http")
    async def trace_middleware(request: Request, call_next):
        tid = tracing.new_trace_id()
        resposta = await call_next(request)
        resposta.headers["X-Trace-Id"] = tid
        return resposta

    @app.exception_handler(RequestValidationError)
    async def validacao(request: Request, exc: RequestValidationError):
        msgs = "; ".join(str(e.get("msg", "")).removeprefix("Value error, ") for e in exc.errors())
        return erro(422, msgs or "Entrada inválida.")

    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest):
        t0 = time.perf_counter()
        try:
            estado = grafo.invoke({"trace_id": tracing.current_trace_id(), "pergunta": req.pergunta})
        except psycopg.Error as e:
            log.exception("falha de banco")
            return erro(502, "O banco de dados está indisponível no momento. Tente novamente em instantes.",
                        req.pergunta, t0, e)
        except Exception as e:  # nunca derruba a API (FR-026)
            log.exception("falha inesperada")
            return erro(502, "Não foi possível processar a pergunta agora.", req.pergunta, t0, e)
        c = estado["classificacao"]
        latencia = int((time.perf_counter() - t0) * 1000)
        modo = estado.get("modo", llm.modo)  # "degradado" se esta requisição caiu para as regras
        resp = AskResponse(
            trace_id=tracing.current_trace_id(), resposta=estado["resposta"], dominio=c.dominio,
            agente=estado["agente"], confianca=c.confianca, fontes=estado.get("fontes", []),
            status=estado["status"], modo=modo, latencia_ms=latencia)
        tracing.record_interaction(
            settings.log_dir, trace_id=resp.trace_id, pergunta=req.pergunta, dominio_previsto=c.dominio,
            confianca=c.confianca, agente=resp.agente, fontes=[f.ref for f in resp.fontes],
            latencia_ms=latencia, status=resp.status, modo=modo, erro=estado.get("erro"))
        return resp

    @app.get("/traces/{trace_id}")
    def trace(trace_id: str):
        registro = tracing.find_trace(settings.log_dir, trace_id)
        if registro is None:
            raise HTTPException(404, "Identificador de rastreio desconhecido.")
        return registro

    @app.get("/health")
    def health():
        return {"status": "ok", "banco": "ok" if db.ping(settings) else "indisponivel", "modo": llm.modo}

    if settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
