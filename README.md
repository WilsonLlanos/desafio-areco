# Aurora — Orquestrador de Agentes de Perguntas

Aplicação web em que um orquestrador (LangGraph) classifica a pergunta e a encaminha ao agente
especializado: **financeiro**, **informações internas** ou **ouvidoria**. Dados sintéticos (empresa fictícia).

> **Estado: Fase 3 de 5.** Funciona: subida via Docker, carga idempotente das bases, `POST /ask` com
> roteamento por regras, agente de ouvidoria (protocolo, filtros, contagens, listas e valores válidos),
> agente financeiro (receitas, despesas, orçamento, execução, inadimplência, comparação), agente de
> informações internas (busca BM25 nos documentos e no FAQ, resposta extrativa com fonte e versão,
> limites de dados individuais), frontend de chat e rastreio por `trace_id`. Ainda não implementados:
> uso do Gemini, recusa de credenciais (AV-T010) e recusa de prompt injection na pergunta. Ver `specs/001-orquestrador-agentes/tasks.md` e `docs/DEVLOG.md`.

## Executar

Pré-requisitos: Docker e Docker Compose.

```bash
cp .env.example .env     # ajuste as senhas; GEMINI_API_KEY é opcional nesta fase
docker compose up --build
```

Abra http://localhost:8000 (se a porta estiver ocupada, defina `APP_PORT` no `.env`). A carga das bases roda sozinha na subida (e pode ser repetida sem duplicar).

Exemplos: `Qual o status do protocolo OUV-0002?`, `Quais status podem aparecer na ouvidoria?`,
`Quanto foi gasto em despesas pagas de janeiro a março de 2025?`, `Qual departamento tem maior orçamento em janeiro de 2026?`,
`Como solicito férias?` e `Quais são as aprovações para uma compra de R$ 12.000?`.

```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"pergunta":"Qual o status do protocolo OUV-0002?"}'
curl -s localhost:8000/traces/<trace_id>     # registro da interação
curl -s localhost:8000/health
```

## Testes

```bash
docker compose run --rm app pytest
```

Os testes não usam rede nem LLM real. Os que dependem do banco são ignorados se ele não responder.

## Logs

Um registro JSON por requisição em `logs/interactions.jsonl` (volume `app_logs`) e no stdout, com
`trace_id`, pergunta, domínio, confiança, agente, fontes, latência, status e erro.

## Estrutura

`app/` (API, orquestrador, agentes, consultas, ingestão), `frontend/` (HTML/CSS/JS), `data/` (bases
fornecidas, somente leitura), `tests/`, `specs/` (spec, plano, tarefas), `docs/` (DEVLOG, conversas).
