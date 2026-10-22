# Implementation Plan: Orquestrador de Agentes de Perguntas (Aurora)

**Branch**: `001-orquestrador-agentes` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-orquestrador-agentes/spec.md`

## Summary

Aplicação web de chat em que um orquestrador classifica a pergunta (financeiro, informações internas, ouvidoria, ambígua, fora de escopo) e a encaminha a um de três agentes. Abordagem: FastAPI com **LangGraph** como orquestrador (grafo de nós e arestas condicionais; sem tool-calling livre); PostgreSQL para as bases tabulares com **consultas pré-definidas e parametrizadas** executadas por um **papel somente leitura**; RAG com **BM25 em memória** sobre os documentos internos e o FAQ; Google Gemini (padrão) apenas para classificar, extrair parâmetros validados e redigir a resposta de informações internas; **roteamento por regras** como degradação sem chave. Respostas financeiras e de ouvidoria são montadas por código (nunca pelo LLM), o que torna os números verificáveis. Entrega em 5 fases com aprovação entre elas.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI + Uvicorn, Pydantic v2, `psycopg[binary]` 3, `rank-bm25`, `langgraph`, `google-genai` (Gemini) (logging JSON com o `logging` padrão)

**Storage**: PostgreSQL 16 (3 tabelas de `data/sql/schema.sql`); índice BM25 em memória reconstruído na subida; log de interações em JSON Lines (volume Docker)

**Testing**: `pytest` com LLM fake injetável, sem rede (lógica); `scripts/evaluate.py` com Gemini real (avaliação AV-T001–AV-T012), fora do pytest

**Target Platform**: Linux em contêiner, via `docker compose up`

**Project Type**: web-service (API + frontend estático servido pela própria API)

**Performance Goals**: ≥90% das respostas em ≤10 s (SC-007); baixa concorrência

**Constraints**: sem SQL gerado pelo LLM; `Decimal`/`NUMERIC` em valores; sem segredos no repositório; `data/` imutável; CSV com `utf-8-sig`; testes sem rede

**Scale/Scope**: 300 lançamentos, 144 linhas de orçamento, 180 manifestações, 10 documentos + 7 itens de FAQ; usuário único, sem autenticação

## Constitution Check

*GATE: passa antes da Fase 0; reavaliado após a Fase 1.*

| Princípio | Como o plano atende | Status |
|---|---|---|
| I. Rastreabilidade | `trace_id` (UUID) gerado em middleware na entrada, propagado em um `contextvar`; um log JSON por requisição com os campos exigidos; `GET /traces/{trace_id}` localiza o registro | OK |
| II. Sem SQL do modelo | Catálogo fixo de consultas em `app/queries/`; LLM só devolve parâmetros validados por Pydantic/enums; app conecta com papel `aurora_ro` (apenas `SELECT` nas 3 tabelas); `Decimal` em todo o cálculo; critério declarado | OK |
| III. Docker Compose | Serviços `db` e `app`; `app` roda ingestão idempotente (upsert) e depois a API; `.env.example` documentado | OK |
| IV. Simplicidade | LangGraph justificado (grafo de roteamento explícito, emenda 1.2.0); sem pgvector/frontend framework; BM25 e fallback por regras justificados em `research.md` | OK |
| V. Testes | `tests/` com `FakeLLM`; financeiro conferido por cálculo independente sobre os CSV; `scripts/evaluate.py` separado, gera `docs/evaluation/*.jsonl`; juiz LLM complementar só nesse script (`scripts/judge.py`, FR-039), sem entrar em `app/` nem no `pytest` (testado com `FakeLLM`) | OK |
| VI. DEVLOG | Cada tarefa e fase de `tasks.md` inclui a atualização de `docs/DEVLOG.md` | OK |
| VII. Sem segredos | `.env` no `.gitignore`; só `.env.example`; log de avaliação sem chave | OK |
| VIII. Fundamentado e com fonte | Fontes definidas por código a partir do que foi recuperado/consultado; "não encontrado" para protocolo inexistente; esclarecimento, escopo e recusa tratados antes dos agentes | OK |
| IX. Fases | 5 fases abaixo, cada uma com gate e commit próprio; avanço só com aprovação | OK |

**Hardening de LLM** (skill `llm-safety-hardening`; briefing §6): defesas estruturais primeiro, prompt por último.

- *Estruturais*: papel de banco somente leitura; consultas fixas; saída do LLM validada contra schema/enums (valor inválido → esclarecimento); fontes e números escritos por código; guarda determinística **antes** do LLM para credenciais/dados de terceiros (AV-T010); limite de tamanho da pergunta; sem ferramentas de escrita nem acesso a rede além do provedor.
- *Dados não confiáveis*: trechos recuperados e pergunta vão delimitados como dados na mensagem; resposta de informações internas é conferida (fonte citada ∈ trechos recuperados).
- *Prompt (2ª camada)*: instrução de escopo e de ignorar instruções embutidas.
- Antes de concluir a Fase 4: smoke test adversarial informal (override, extração de prompt, fabricação, injeção em chunk, multi-turno não se aplica por ser single-turn, ofuscação), reportado como spot-check.

Sem violações; **Complexity Tracking** vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-orquestrador-agentes/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.openapi.yaml
│   └── llm-schemas.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
app/
├── main.py              # FastAPI, middleware de trace_id, rotas, estáticos
├── config.py            # variáveis de ambiente (os.environ)
├── api/schemas.py       # AskRequest / AskResponse
├── orchestrator.py      # grafo LangGraph: guard → classify → agente/esclarecer/escopo → finalizar
├── guards.py            # recusas determinísticas, validação de entrada
├── llm/
│   ├── base.py          # protocolo LLMClient (classify, extract_params, answer)
│   ├── gemini.py        # implementação Gemini
│   └── rules.py         # roteamento/extração por regras (degradação sem chave)
├── agents/
│   ├── base.py          # Resultado, formatação em reais e percentuais
│   ├── internal.py      # RAG
│   ├── ouvidoria.py
│   └── financeiro.py
├── rag/index.py         # chunking por seção + BM25 + metadados
├── queries/             # consultas parametrizadas (ouvidoria.py, financeiro.py)
├── db.py                # conexão (papel ro) e helpers
├── periodo.py           # períodos em português → intervalos de datas
├── ingestion.py         # CSV→Postgres idempotente, papel ro, valida enums
└── tracing.py           # contextvar trace_id, logger JSON, gravação JSONL
frontend/                # index.html, style.css, app.js
scripts/evaluate.py      # avaliação AV-T001–AV-T012 com LLM real
scripts/judge.py         # juiz LLM complementar (Gemini Pro, JUDGE_MODEL); só usado pela avaliação
tests/                   # unit, integração (Postgres de teste), acceptance com FakeLLM
docs/                    # briefing.md, DEVLOG.md, arquitetura, decisões, limitações, evaluation/
Dockerfile, docker-compose.yml, .env.example, requirements.txt, README.md, CLAUDE.md
```

**Structure Decision**: projeto único (backend servindo o frontend estático), alinhado à seção 9 do briefing; um serviço a menos no compose.

## Fases de entrega (constituição IX)

1. **Fase 1 — Fatia vertical**: Docker Compose, ingestão idempotente, papel `ro`, `POST /ask` com roteamento por regras, agente de ouvidoria (protocolo exato), frontend mínimo, `trace_id` + log JSONL, `CLAUDE.md` (inclui a instrução de guardar o histórico das conversas desde o início, em `docs/conversas/`), DEVLOG (com o registro da emenda 1.2.0). Cobre AV-T004, AV-T009.
2. **Fase 2 — Ouvidoria completa e Financeiro**: filtros e referência (AV-T005); catálogo financeiro com critério declarado (AV-T006, AV-T007, AV-T011); testes com cálculo independente.
3. **Fase 3 — Informações internas (RAG)**: chunking, BM25, extrativo sem chave; limites e encaminhamentos (AV-T001–T003, T008, T012).
4. **Fase 4 — Gemini e segurança**: classificação com confiança, extração de parâmetros, redação do agente interno, esclarecimento/fora de escopo/recusa (AV-T010), erros do provedor, smoke test adversarial.
5. **Fase 5 — Avaliação e documentação**: `scripts/evaluate.py` + log de avaliação versionado e log de amostra das interações (`docs/evaluation/`, sem dados sensíveis), README, arquitetura/decisões/limitações, seção de pendências (o que ficou pendente, o que foi tentado, como concluir, o que faria diferente), revisão de segredos e exportação sanitizada das conversas.

## Complexity Tracking

Sem violações a justificar.
