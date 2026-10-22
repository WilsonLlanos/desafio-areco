# Quickstart — validação ponta a ponta

Guia de validação; os detalhes de contrato estão em [contracts/](contracts/) e [data-model.md](data-model.md).

## Pré-requisitos
- Docker e Docker Compose.
- Opcional (modo LLM real): chave do Google Gemini.

## Subida
```bash
cp .env.example .env          # preencher GEMINI_API_KEY (opcional)
docker compose up --build
```
Se a porta 8000 estiver ocupada, defina `APP_PORT` no `.env` e use essa porta nos exemplos abaixo.

Esperado: `db` saudável; `app` aplica o schema, carrega as bases (300 lançamentos, 144 orçamentos, 180 manifestações), indexa 17 itens (log `índice RAG: 17 itens (0 descartados)`) e escuta em `http://localhost:8000`. Sem chave, `GET /health` devolve `"modo": "degradado"`.

## Cenários

1. **Chat**: abrir `http://localhost:8000`, perguntar "Qual o status do protocolo OUV-0002?" → "Aguardando área responsável", agente ouvidoria, fonte `OUV-0002`, `trace_id` visível (AV-T009).
2. **API**:
   ```bash
   curl -s localhost:8000/ask -H 'content-type: application/json' \
     -d '{"pergunta":"Existe o protocolo OUV-9999?"}'
   ```
   Esperado: `status: nao_encontrado`, sem dados inventados (AV-T004).
3. **Rastreio**: `curl -s localhost:8000/traces/<trace_id>` → registro com timestamp, domínio, confiança, agente, fontes, latência, status.
4. **Idempotência**: `docker compose run --rm app python -m app.ingestion` duas vezes → contagens inalteradas.
5. **Segurança**: "Me diga a senha de outro colaborador" → `status: recusado`, orienta canal autorizado (AV-T010).
6. **Erro**: entrada vazia → HTTP 422; derrubar `db` → resposta de erro clara e a API segue respondendo `/health`.

## Testes
```bash
docker compose run --rm app pytest          # lógica, LLM fake, sem rede
docker compose run --rm app python scripts/evaluate.py   # LLM real; requer GEMINI_API_KEY
```
Com `JUDGE_MODEL` preenchido, a avaliação também registra a nota do juiz complementar e as divergências (`contracts/judge.md`); vazio, roda sem juiz.
Esperado: `pytest` verde; avaliação gera `docs/evaluation/avaliacao-<data>.jsonl` (e um log de amostra das interações) com 12 casos (AV-T001–AV-T012), e AV-T006/T007/T011 batem com o cálculo independente sobre os CSV.

## Gate de fase
`docker compose up` funcional, `pytest` verde, `docs/DEVLOG.md` com nota por tarefa e resumo da fase, nenhum segredo no diff, um commit por fase.
