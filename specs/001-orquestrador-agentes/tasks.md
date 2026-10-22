---
description: "Task list — Orquestrador de Agentes de Perguntas (Aurora)"
---

# Tasks: Orquestrador de Agentes de Perguntas (Aurora)

**Input**: `specs/001-orquestrador-agentes/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: solicitados (constituição V). Testes `pytest` usam `FakeLLM`, sem rede. Casos de avaliação são sempre `AV-Txxx`; IDs de tarefa são `Txxx`.

## Format: `- [ ] [ID] [P?] [Story?] Descrição com caminho`

- **[P]**: pode rodar em paralelo (arquivos distintos, sem dependência pendente)
- **[US1–US5]**: user story da spec (US1 resposta do domínio certo, US2 respostas seguras, US3 execução reproduzível, US4 rastreio, US5 avaliação)

## Regras transversais (constituição)

- **Toda tarefa**, ao concluir, recebe uma nota curta em `docs/DEVLOG.md` (o que foi feito, decisão/problema, sugestão de IA aceita/modificada/descartada, teste executado) (VI). O histórico das conversas é exportado uma única vez, na T065: a sessão do Claude Code atravessa várias fases, e exportar por fase geraria cópias parciais da mesma conversa (decisão após `/speckit-analyze`, 2026-10-21).
- **Pré-fase concluída**: `CLAUDE.md`, `docs/DEVLOG.md` (histórico retroativo) e `docs/conversas/README.md` já existem; T001, T002 e T065 não os recriam.
- **Cada fase** termina com tarefa de **gate**: `docker compose up` funcional, `pytest` verde, resumo da fase no DEVLOG, nenhum segredo no diff, **um commit** e **parada para aprovação explícita** antes da fase seguinte (IX).
- `data/` nunca é alterado. CSVs lidos com `utf-8-sig`. Valores monetários sempre `Decimal`.

---

## Fase 1 — Fatia vertical (US3, US4, parte de US1)

**Objetivo**: ambiente sobe com um comando, ingestão idempotente, `POST /ask` com roteamento por regras, ouvidoria por protocolo, frontend mínimo e rastreio.

**Entrega verificável**: AV-T004 e AV-T009 respondem pela UI; `/traces/{id}` devolve o registro; ingestão repetida não duplica.

### Setup

- [X] T001 `CLAUDE.md` na raiz com a regra de registro contínuo no DEVLOG e de guarda das conversas em `docs/conversas/` — **já criado antes da Fase 1** (pré-fase); na Fase 1, apenas revisar o arquivo e atualizá-lo se o fluxo mudar
- [X] T002 [P] `docs/DEVLOG.md` com formato de nota/resumo e o histórico retroativo da pré-fase (inclui a emenda 1.2.0) — **já criado antes da Fase 1**; na Fase 1, apenas acrescentar as notas das tarefas e o resumo da fase
- [X] T003 [P] Criar `.gitignore` (inclui `.env`, `logs/`, `__pycache__/`, `.pytest_cache/`) e `.env.example` sem valores reais (`GEMINI_API_KEY`, `GEMINI_MODEL=gemini-3.1-flash-lite`, `CONFIDENCE_THRESHOLD=0.6`, `POSTGRES_*`, `DB_RO_PASSWORD`, `LOG_DIR`)
- [X] T004 [P] Criar `requirements.txt` (fastapi, uvicorn, pydantic, psycopg[binary], rank-bm25, langgraph, google-genai, pytest, httpx) com versões fixadas — **desvio**: `google-genai` adiado para T045 (YAGNI); `rank-bm25` adiado para T038 e lá **descartado** (BM25 próprio; ver DEVLOG e research §1)
- [X] T005 Criar `Dockerfile` (Python 3.12, usuário não-root) e `docker-compose.yml` (`db` PostgreSQL 16 com healthcheck; `app` depende de `db`; `data/` montado somente leitura; volume `logs/`)
- [X] T006 Criar estrutura de pacotes `app/`, `app/api/`, `app/llm/`, `app/agents/`, `app/rag/`, `app/queries/`, `tests/`, `frontend/`, `scripts/` com `__init__.py`

### Base (bloqueia as histórias)

- [X] T007 `app/config.py`: leitura de variáveis de ambiente com padrões e validação
- [X] T008 `app/db.py`: conexão psycopg com papel `aurora_ro` e helper de consulta parametrizada; tratamento de banco indisponível
- [X] T009 `app/ingestion.py`: aplica `data/sql/schema.sql`, lê os 3 CSV (`utf-8-sig`), valida datas e enums contra `referencia_ouvidoria.json`, converte `valor_brl` para `Decimal`, faz upsert por chave primária, cria o papel `aurora_ro` com `SELECT` apenas; aborta com arquivo/linha em dado inválido
- [X] T010 [P] `tests/test_ingestion.py`: contagens (300/144/180), idempotência (duas execuções), rejeição de enum inválido, `Decimal` preservado, papel `ro` sem permissão de escrita
- [X] T011 `app/tracing.py`: `trace_id` UUID4 em `contextvar`, logger JSON, gravação em `logs/interactions.jsonl` com os campos de `data-model.md`, sem segredos
- [X] T012 `app/api/schemas.py`: `AskRequest`, `AskResponse`, `Fonte`, `Classificacao`, `Erro` conforme `contracts/api.openapi.yaml`
- [X] T013 `app/llm/base.py`: protocolo `LLMClient` (`classify`, `extract_params`, `answer`) e `FakeLLM` injetável para testes
- [X] T014 `app/llm/rules.py`: `RulesLLM` com classificação por regex/palavras-chave (protocolo `OUV-\d{4}`, termos financeiros, de ouvidoria e de políticas) e extração de parâmetros de ouvidoria
- [X] T015 `app/guards.py`: validação de entrada (vazia, só símbolos, > 1000 caracteres → 422)

### US3 — Execução reproduzível

- [X] T016 [US3] Ponto de entrada do `app`: executa `python -m app.ingestion` e depois sobe Uvicorn; `GET /health` em `app/main.py` (banco, modo `llm`/`degradado`)
- [X] T017 [US3] Rascunho inicial do `README.md` com o passo a passo de subida (clone, `.env`, `docker compose up`) e o primeiro teste de pergunta

### US1/US4 — Pergunta, ouvidoria por protocolo e rastreio

- [X] T018 [P] [US1] `app/queries/ouvidoria.py`: `buscar_protocolo` parametrizada (regex `^OUV-\d{4}$`, maiúsculas), enums da base de referência
- [X] T019 [US1] `app/agents/ouvidoria.py`: busca exata, resposta por template em código com status, datas de abertura/resposta e fonte `{protocolo}`; sem correspondência → `status=nao_encontrado` (FR-009, FR-013)
- [X] T020 [US1] `app/orchestrator.py` (versão mínima em LangGraph): nós `guard → classify → agente_ouvidoria / esclarecer / fora_de_escopo → finalizar`, estado tipado com `trace_id`; domínios ainda não implementados devolvem aviso claro
- [X] T021 [US4] `app/main.py`: middleware de `trace_id` (cabeçalho `X-Trace-Id`), `POST /ask`, `GET /traces/{trace_id}`, tratamento de erro sem derrubar a API (502 em falha de dependência)
- [X] T022 [P] [US1] `frontend/index.html`, `frontend/style.css`, `frontend/app.js`: campo de pergunta, carregando, erro, resposta, domínio/agente/confiança, fontes, `trace_id` e aviso de modo degradado (FR-024); servido por `StaticFiles`
- [X] T023 [P] [US4] `tests/test_tracing.py`: um registro por requisição com todos os campos; falha registra o erro com o mesmo `trace_id`; resposta e cabeçalho expõem o id
- [X] T024 [P] [US1] `tests/test_ouvidoria_protocolo.py`: AV-T009 (OUV-0002 → "Aguardando área responsável"), AV-T004 (OUV-9999 → não encontrado), `OUV-12` e minúsculas
- [X] T025 [P] [US1] `tests/test_api.py`: 422 para entrada vazia/longa, `/health`, banco indisponível → erro claro e API ativa

### Gate

- [X] T026 Gate da Fase 1: rodar `quickstart.md` (cenários 1–4 e 6), `pytest` verde, resumo da Fase 1 no DEVLOG, checar ausência de segredos, **commit da fase** e **aguardar aprovação**

---

## Fase 2 — Ouvidoria completa e Financeiro (US1)

**Objetivo**: AV-T005, AV-T006, AV-T007 e AV-T011 respondidos por código determinístico, com critério declarado.

**Teste independente**: perguntas financeiras e de ouvidoria por filtro retornam valores iguais ao cálculo independente sobre os CSV.

- [X] T027 [P] [US1] `app/queries/ouvidoria.py`: `contar` e `listar` com filtros (status, categoria, prioridade, canal, intervalo de `data_abertura`) e `referencia` (enums de `referencia_ouvidoria.json`)
- [X] T028 [US1] `app/agents/ouvidoria.py`: consultas por filtro, contagens/listas (no máximo 10 itens + total, orientando refinar o filtro; FR-010), distinção abertura × resposta e "Respondido" × "Concluído", prazo de 10 dias como parâmetro demonstrativo (FR-010 a FR-012)
- [X] T029 [P] [US1] `app/queries/financeiro.py`: `soma_despesas`, `soma_receitas`, `receita_liquida`, `comparar_periodos`, `orcamento_por_departamento`, `execucao_orcamentaria`, `inadimplencia`; colunas por whitelist, `NUMERIC`, `tipo_data` (padrão competência) e `criterio_gasto` (padrão **incorrida**)
- [X] T030 [US1] `app/agents/financeiro.py`: valida `ParamsFinanceiro`, executa a consulta, renderiza resposta por template em reais com o critério declarado (tipo, status, tipo de data, período, centro de custo/departamento) e fontes (consulta + arquivo + até 10 IDs `FIN-xxxx` e total); período ausente → esclarecimento (FR-035); `receita_liquida` = soma das receitas declarando que não há deduções (FR-036); sem dados → "sem dados no período" (FR-014 a FR-018)
- [X] T031 [US1] `app/llm/rules.py`: extração por regex de período, mês/ano em português, tipo, status, departamento e centro de custo para financeiro; `CC100–CC600`
- [X] T032 [US1] `app/orchestrator.py`: nó `agente_financeiro`, ramos de esclarecimento por parâmetro ausente, dois domínios candidatos ≥ 0,5 → esclarecimento (FR-005)
- [X] T033 [P] [US1] `tests/oracle.py`: cálculos independentes em Python puro (`csv` + `Decimal`) sobre os arquivos de `data/` para soma de receitas 2025, despesas pagas jan–mar/2025, maior orçamento jan/2026, contagens de ouvidoria
- [X] T034 [P] [US1] `tests/test_financeiro.py`: AV-T006, AV-T007, AV-T011 iguais ao oráculo (centavo); gasto sem critério → incorrida declarada; paga × incorrida; competência × vencimento; ano fora de 2025–2026; período ausente → esclarecimento; receita líquida igual à soma das receitas, com aviso
- [X] T035 [P] [US1] `tests/test_ouvidoria_filtros.py`: AV-T005 lista apenas os status do JSON; listas limitadas a 10 itens com o total; contagens e listas por filtro iguais ao oráculo
- [X] T036 [P] [US1] `tests/test_routing_multidominio.py`: pergunta que cruza domínios (ex.: reembolso) → esclarecimento, sem combinar agentes
- [X] T037 Gate da Fase 2: `pytest` verde, `docker compose up`, resumo no DEVLOG, sem segredos, **commit** e **aguardar aprovação**

---

## Fase 3 — Informações internas / RAG (US1, US2)

**Objetivo**: AV-T001, AV-T002, AV-T003, AV-T008 e AV-T012 respondidos só com os trechos recuperados, com fonte, funcionando também sem chave (resposta extrativa).

**Teste independente**: cada pergunta devolve o conteúdo-chave do critério e o arquivo-fonte esperado.

- [X] T038 [US1] `app/rag/index.py`: leitura de `data/informacoes_internas/*.md` e `faq_interno.json`, um item por documento e por pergunta do FAQ, metadados `domain`, `source`, `secao`, `document_version`, BM25 com normalização (minúsculas, sem acentos, stopwords PT), top-3 e escore mínimo; BM25 próprio, sem dependência nova (**desvio** do plano: `rank-bm25` traria `numpy`; ver research §1 e DEVLOG); criar `detectar_injecao(texto)` em `app/guards.py` (regex sobre texto normalizado — minúsculas, sem acentos — em PT e EN: override "ignore/desconsidere as instruções", extração de prompt "prompt do sistema"/"revele suas instruções", roleplay/jailbreak "você agora é"/"aja como"/"modo desenvolvedor"/"DAN", marcadores de papel `system:`/`<|...|>`) e usá-la na indexação: trecho que casar é registrado em log com aviso e **não é indexado** (injeção indireta, FR-029)
- [X] T039 [US1] `app/agents/internal.py`: recupera trechos; sem trecho acima do escore → "não encontrei na base"; resposta extrativa (sem LLM) com valores e prazos copiados do texto; fontes `{arquivo, seção/FAQ-id}` definidas por código (FR-006, FR-008)
- [X] T040 [US2] `app/agents/internal.py`: limites dos documentos — não confirmar saldo individual, não consultar holerite, não interpretar caso trabalhista, não revelar dados de terceiros; encaminhar ao RH (FR-007)
- [X] T041 [US1] `app/orchestrator.py`: nó `agente_internas`; `RulesLLM` decide internas × fora de escopo pelo escore do BM25
- [X] T042 [P] [US1] `tests/test_rag.py`: recuperação do arquivo esperado para AV-T001, AV-T002, AV-T003, AV-T008, AV-T012; conteúdo-chave (30 dias, 10 dias corridos e comprovante, liderança + gerente + diretoria, `seguranca@aurora.example`, reporte imediato sem segredos no chamado); FAQ indexado
- [X] T043 [P] [US2] `tests/test_internal_limits.py`: holerite/saldo de férias individual → informa falta de acesso e encaminha ao RH; pergunta sem resposta na base → não inventa
- [X] T043a [P] [US2] `tests/test_injecao_rag.py`: `detectar_injecao` casa os padrões (PT/EN, acentos, maiúsculas) e não casa textos legítimos com "instruções"; documento com instrução embutida (diretório de dados temporário) não é indexado, é registrado em log e não altera a resposta; os 10 documentos reais continuam indexados
- [X] T044 Gate da Fase 3: `pytest` verde, `docker compose up`, resumo no DEVLOG, sem segredos, **commit** e **aguardar aprovação**

---

## Fase 4 — Gemini e segurança (US1, US2)

**Objetivo**: classificação com confiança, extração de parâmetros e redação via Gemini, esclarecimento/escopo/recusa, erros do provedor e hardening.

**Teste independente**: pedido de senha é recusado antes do LLM; saída inválida do modelo vira esclarecimento; sem chave a API segue em modo degradado.

- [X] T045 [US1] `app/llm/gemini.py`: cliente `google-genai` com `GEMINI_MODEL=gemini-3.1-flash-lite`, saída estruturada (`response_schema`) para classificação e parâmetros, timeout de 8 s (**desvio**: `response_json_schema` e 10 s, mínimo da API; ver DEVLOG); validar o id do modelo e o suporte a saída estruturada, registrando o resultado no DEVLOG; incluir `google-genai` (versão fixada) no `requirements.txt`; o `response_schema` segue `contracts/llm-schemas.md` (inclui `receita_liquida`, comparação, `ordem` e `referencia_tipo`)
- [X] T046 [US1] Validação Pydantic das saídas do LLM conforme `contracts/llm-schemas.md`; valor fora de enum/formato → parâmetro ausente → esclarecimento
- [X] T047 [US1] `app/orchestrator.py`: seleção `GeminiLLM` × `RulesLLM` por `GEMINI_API_KEY`, `modo` na resposta, limiar de confiança 0,6, fallback para regras na classificação quando o provedor falha (FR-034, FR-026)
- [X] T048 [US1] `app/agents/internal.py`: redação via `LLMClient.answer` com pergunta e trechos delimitados como dados; descartar a resposta se `fontes_usadas` ⊄ trechos recuperados e usar a versão extrativa
- [X] T049 [US2] `app/guards.py`: guarda determinística pré-LLM para credenciais, senhas e dados de terceiros (AV-T010, FR-028) com orientação aos canais de segurança/privacidade citando `04_seguranca_da_informacao.md` e `09_politica_privacidade.md`
- [X] T049a [US2] `app/guards.py`: `recusa()` **reaproveita** `detectar_injecao` (criada na T038) sobre a pergunta: injeção detectada → recusa com explicação de escopo antes do LLM (nó `guard`, sem mudar o grafo; injeção direta, FR-029); ampliar os padrões se o smoke test (T054) mostrar lacunas. Sem classificador por modelo: decisão no DEVLOG
- [X] T050 [US2] `app/orchestrator.py`: ramos de esclarecimento (ambígua/baixa confiança), fora de escopo com explicação dos três domínios (FR-003, FR-004)
- [X] T051 [P] [US2] `tests/test_guards.py`: AV-T010 recusa sem chamar o LLM; variações de redação do pedido
- [X] T051a [P] [US2] `tests/test_guards.py`: injeção (override PT/EN, extração de prompt, roleplay/DAN, acentos/maiúsculas) → recusa sem chamar o `FakeLLM`; perguntas legítimas com "instruções" (ex.: "quais as instruções para pedir reembolso?") → não recusadas
- [X] T052 [P] [US2] `tests/test_llm_contracts.py`: com `FakeLLM`, saída malformada, enum inválido, campo extra e fonte fora dos trechos são rejeitados; falha do provedor gera erro claro e log com o mesmo `trace_id`
- [X] T053 [P] [US2] `tests/test_routing.py`: ambígua → esclarecimento, fora de escopo → explicação, baixa confiança, modo degradado marcado na resposta
- [X] T054 [US2] Smoke test adversarial informal contra a função que fala com o modelo (override de instruções, extração de prompt, fabricação de protocolo/valor, injeção em trecho recuperado, ofuscação/outro idioma): registrar prompts e resultados no DEVLOG como spot-check, não auditoria
- [X] T055 Gate da Fase 4: `pytest` verde, `docker compose up` com e sem chave, resumo no DEVLOG, sem segredos, **commit** e **aguardar aprovação**

---

## Fase 5 — Avaliação e documentação (US5, US3, US4)

**Objetivo**: evidência objetiva com LLM real e entrega documentada, inclusive o que ficou pendente.

**Teste independente**: `scripts/evaluate.py` gera o log com 12 linhas; um clone limpo sobe seguindo só o README.

- [ ] T056 [US5] `scripts/evaluate.py`: lê `data/testes/perguntas_avaliacao.json`, chama `POST /ask` com LLM real, verifica domínio (AV-T010 aceita recusa), fonte esperada ∈ fontes e conteúdo-chave por caso; compara AV-T006/T007/T011 ao oráculo; grava `docs/evaluation/avaliacao-<data>.jsonl` (por caso: `trace_id`, esperado × obtido, critério, resultado, latência) e imprime tabela; calcula o p90 de latência total e o p90 só dos casos com `modo=llm`, comparando com a meta de 10 s (SC-007). Grava o `modo` de cada caso; o script (não a aplicação) repete até 2 vezes o caso que sair `degradado`; se continuar degradado, o resultado é `nao_avaliado_llm`, não aprovado. O resumo separa "aprovados com LLM", "aprovados em modo degradado" e "não avaliados com LLM"
- [ ] T056a [US5] `scripts/judge.py`: juiz complementar conforme `contracts/judge.md` (Gemini Pro em `JUDGE_MODEL`, mesma `GEMINI_API_KEY`, `response_json_schema`, temperatura 0, pergunta/resposta delimitadas como dados, referência por caso); integrar ao `evaluate.py` com `juiz_modelo`, `juiz` e `divergente` no log e contagem de divergências no resumo; sem `JUDGE_MODEL` → `nao_executado`; falha → `erro`, sem reprovar o caso; validar o id do modelo na conta (por exemplo `gemini-2.5-pro`, `gemini-3.1-pro-preview` ou `gemini-pro-latest`) e registrar no DEVLOG (FR-039)
- [ ] T056b [US5] `tests/test_judge.py` com `FakeLLM`: montagem da entrada (referência certa por domínio, delimitação), validação do schema (saída inválida → `erro`), regra de `divergente` nos dois sentidos, `JUDGE_MODEL` ausente → `nao_executado`, falha do juiz não reprova; garantir que nenhum módulo de `app/` importa `scripts.judge`
- [ ] T057 [US5] Executar a avaliação com `GEMINI_API_KEY` real, conferir ausência de segredos no log e versionar o resultado; gerar também o log de amostra das interações em `docs/evaluation/interacoes-amostra.jsonl` sem dados sensíveis
- [ ] T058 [US5] Analisar falhas da avaliação, ajustar e reexecutar; registrar tentativas e decisões no DEVLOG
- [ ] T059 [P] [US3] `README.md` final: pré-requisitos, passo a passo, variáveis, subida, testes (`pytest` e avaliação), estrutura do repositório, solução de problemas; seção "Segurança" com as camadas (guarda pré-LLM, detector de injeção, trechos delimitados, consultas fixas com papel `ro`, números e fontes por código), limitações (regex não cobre paráfrases/ofuscação) e "a implementar" (classificador dedicado, ex.: Prompt Guard ou LLM como juiz, e conjunto adversarial maior); seção "Integração contínua" (o que o CI valida, que roda sem chave do LLM) e o badge do workflow
- [ ] T060 [P] `docs/arquitetura.md`: visão geral, diagrama do grafo LangGraph (`draw_mermaid`), fluxo de dados, papéis de banco, rastreabilidade
- [ ] T061 [P] `docs/decisoes.md`: decisões do briefing §8 e do clarify (LangGraph, BM25, Gemini, esclarecimento multi-domínio, incorrida, formato de fontes), alternativas descartadas; inclui o juiz de avaliação (Gemini Pro, complementar) e a alternativa de outra família como melhoria futura
- [ ] T062 [P] `docs/limitacoes.md`: limitações conhecidas e **pendências**: o que ficou pendente, o que foi tentado e por que não funcionou, como concluir, o que faria diferente; inclui que o log grava a pergunta como digitada (exigência da constituição I), então dado pessoal digitado pelo usuário vai para o log; inclui o viés de mesma família do juiz e a mitigação (referência + rubrica + temperatura 0 + decisão determinística)
- [ ] T063 [P] [US4] Documentar em `docs/arquitetura.md` como consultar logs (`/traces/{id}` e `logs/interactions.jsonl`) e a política de dados nos logs
- [X] T064 Atualizar a seção "Decisões em aberto" de `specs/001-orquestrador-agentes/spec.md` com as decisões tomadas e corrigir a numeração/estado nos documentos — **feito após `/speckit-analyze`** (seção substituída por "Decisões da seção 8 do briefing")
- [ ] T065 Exportar o histórico das conversas para `docs/conversas/` conforme a tabela de `docs/conversas/README.md` (README já criado na pré-fase; alternativa documentada se a exportação for parcial), removendo chaves, tokens, credenciais e e-mail, e revisar a sanitização; atualizar a coluna "Exportado"
- [ ] T066 Verificação final em clone limpo: seguir só o README, medir o tempo até a primeira resposta (meta SC-005 ≤ 15 min), rodar `quickstart.md` completo, revisar o diff por segredos; confirmar o run verde do CI no GitHub para o commit final
- [ ] T067 Gate da Fase 5: `pytest` verde, DEVLOG com resumo final, **commit** e **aguardar aprovação**; rodar `pytest` 3 vezes seguidas no contêiner, todas verdes (SC-008)

---

## Dependências e ordem

- Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5, **cada avanço só com aprovação explícita**.
- Dentro da Fase 1: T001–T006 → T007–T015 (base) → T016–T025; T018, T022, T023, T024, T025 são paralelizáveis após T012–T015.
- Fase 2: T027 e T029 em paralelo; T028 depende de T027; T030 de T029; T032 de T028 e T030; testes T033–T036 em paralelo após os agentes.
- Fase 3: T038 → T039 → T040 → T041; testes (T042, T043, T043a) em paralelo.
- Fase 4: T045 e T049 independentes; T047 depende de T045 e T046; T054 depois de T048–T050.
- Fase 5: T056 → T056a → T057 → T058 (T056b depois de T056a); documentação T059–T063 em paralelo; T065 e T066 por último.

## Cobertura das user stories

| Story | Tarefas principais |
|---|---|
| US1 | T018–T022, T027–T036, T038–T042, T045–T048 |
| US2 | T040, T043, T043a, T049–T054 (inclui T049a, T051a) |
| US3 | T003–T005, T009, T016, T017, T059, T066 |
| US4 | T011, T021, T023, T063 |
| US5 | T056, T056a, T056b, T057, T058 |

## Estratégia de implementação

- **MVP**: Fase 1 (fatia vertical executável por Docker com rastreio), conforme a orientação do briefing de priorizar o fluxo ponta a ponta.
- **Entrega parcial é aceitável** (e-mail do desafio): se o tempo acabar, a fase corrente é documentada em `docs/limitacoes.md` com o que falta e como concluir.
