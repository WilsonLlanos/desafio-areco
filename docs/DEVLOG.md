# DEVLOG — Desafio Aurora

Registro contínuo do desenvolvimento com IA (constitution, princípio VI). Formato:

- **Nota de tarefa**: `### [data] Txxx — título` com o que foi feito, decisão/problema, sugestão de IA
  (aceita/modificada/descartada) e teste executado.
- **Resumo de fase**: objetivo, o que funciona, decisões técnicas, problemas e soluções, testes e
  validações, limitações e pendências.
- Entradas reconstruídas depois do fato são marcadas **(registrado retroativamente)** e citam a fonte.

---

## Pré-fase — Especificação e planejamento (registrado retroativamente)

> **Registrado retroativamente em 2026-10-21**, a partir de: histórico git, artefatos em `specs/` e
> `.specify/`, e as três sessões do Claude Code listadas em `docs/conversas/README.md`. Da sessão
> `086d1831…` só os pedidos do usuário foram revisados, não o conteúdo integral. Datas em horário
> local (UTC−3); os carimbos das sessões estão em UTC.

### 2026-10-20 — Setup e insumos
- Setup do Spec Kit (`ad78376`), bases de conhecimento em `data/` (`ec37adc`) e `docs/briefing.md` (`47f435f`).
- O briefing consolida o desafio e as regras que vêm dos dados (ingestão, orquestração, domínio, logs) e deixa 6 decisões em aberto (§8).
- Sessão `086d1831…`: o usuário pediu a leitura de todos os arquivos de `data/`, começando por `ingestao_e_uso.md` e `dicionario_de_dados.md`, e a consolidação do desafio como entrada do `/speckit.specify`.

### 2026-10-20 — Constituição v1.0.0 → v1.1.1 (sessão `086d1831…`)
- Princípios derivados do briefing: rastreabilidade, consultas parametrizadas sem SQL do modelo, Docker Compose, simplicidade, testes, DEVLOG, sem segredos, respostas com fonte, entrega por fases.
- **Correção do usuário**: o item de testes estava misturado. Separou-se `pytest` com LLM mockada (lógica) do script de avaliação com LLM real (AV-T001–T012, com log de execução); o princípio do DEVLOG foi expandido para nota por tarefa + resumo por fase (v1.1.0, `8d93d36`).
- v1.1.1 (`5e6dd99`): casos de avaliação passam a ser `AV-Txxx` para não colidir com IDs de tarefas.

### 2026-10-20 — Spec (sessão `086d1831…`)
- `spec.md` criada a partir do briefing com 5 user stories, 34 requisitos e 8 critérios de sucesso.
- Por pedido do usuário, as decisões em aberto da §8 foram mantidas e deixadas para o clarify; 3 viraram marcadores `[NEEDS CLARIFICATION]` (FR-005, FR-017, FR-034).

### 2026-10-21 — Clarify (sessões `11317751…` e `d859bda9…`)
- A sessão `11317751…` iniciou o `/speckit-clarify` e foi **interrompida pelo usuário** (a transcrição registra a interrupção; o `git` estava limpo no início da sessão seguinte).
- Na sessão `d859bda9…`, o usuário respondeu as três pendências:
  - FR-005 multi-domínio → **pedir esclarecimento**, sem combinar agentes (aceita a recomendação).
  - FR-017 "gasto" sem critério → **despesa incorrida**, sempre declarada (**recomendação da IA era "paga"; usuário escolheu outra**).
  - FR-034 → **Google Gemini** como padrão e **fallback por regras** sem chave (o usuário escolheu "Outro provedor" e depois Gemini, em vez da recomendação Anthropic).
- Aplicado em `spec.md` (seção Clarifications) e `checklists/requirements.md`, sem conflito com a constituição.

### 2026-10-21 — Plano (sessão `d859bda9…`)
- `/speckit-plan` gerou `plan.md`, `research.md`, `data-model.md`, `contracts/` e `quickstart.md`. Constitution Check sem violações.
- Escolhas da IA aceitas: BM25 em memória no lugar de pgvector (funciona sem chave); papel de banco `aurora_ro` somente leitura; guarda determinística pré-LLM; fases 1–5.
- Aplicada a skill `llm-safety-hardening`: defesas estruturais primeiro, prompt como 2ª camada; smoke test adversarial previsto na Fase 4.
- **Descartada pelo usuário**: a recomendação do briefing de implementação própria sem framework. O usuário optou por **LangGraph** e pelo modelo `gemini-3.1-flash-lite`.
- **Correção**: o cabeçalho da spec dizia que se trabalha em `master`; corrigido para `main`.
- **Emenda 1.2.0 da constituição** (princípio IV): frameworks de agentes permitidos; LangGraph apenas para o grafo de orquestração, sem tool-calling livre.
- A IA informou que não havia lido o e-mail do desafio (não estava no repositório); após o usuário colá-lo, confirmou-se que ele não cita LangChain/LangGraph. Daí três ajustes: log de amostra das interações versionado, guarda do histórico das conversas desde a Fase 1 e seção de pendências na documentação final.

### 2026-10-21 — Tarefas (sessão `d859bda9…`)
- `/speckit-tasks` gerou `tasks.md` com 67 tarefas em 5 fases, cada uma com gate, commit próprio e parada para aprovação.
- Tarefas de testes incluídas (constituição V). MVP: Fase 1.

### Pendências herdadas da pré-fase
- Confirmar o id `gemini-3.1-flash-lite` e o suporte a saída estruturada (T045).
- A seção "Decisões em aberto" da spec ainda lista as decisões como abertas (T064).
- Nenhum código de aplicação foi escrito até aqui; nenhum teste foi executado.
- Os artefatos de `specs/`, a emenda 1.2.0, `CLAUDE.md`, este DEVLOG e `docs/conversas/` ainda não foram commitados.

---

## Fase 1 — Fatia vertical

> Notas escritas no fim da implementação da fase, a partir do que foi feito na sessão `d859bda9…`.

### 2026-10-21 — T003–T006 Setup
- `.gitignore`, `.dockerignore` (extra, não estava em `tasks.md`), `.env.example` sem valores reais, `requirements.txt` com versões fixadas, `Dockerfile` (Python 3.12, usuário não-root) e `docker-compose.yml` (`db` com healthcheck, `app`, `data/` somente leitura, volume de logs).
- **Decisão**: `google-genai` e `rank-bm25` ficaram fora do `requirements.txt` até as fases que os usam (3 e 4), por YAGNI; `tasks.md` T004 os listava.
- **Problema**: este WSL não tem Docker nem PostgreSQL. Verificação feita com Python 3.12 (uv) e um PostgreSQL embutido via `pgserver` instalado **só no ambiente local de teste**, fora do `requirements.txt`.

### 2026-10-21 — T007–T015 Base
- `config.py`, `db.py`, `ingestion.py`, `tracing.py`, `api/schemas.py`, `llm/base.py` (`FakeLLM`), `llm/rules.py`, `guards.py`.
- **Decisão**: o parsing/validação dos CSV é separado do upsert, para testar enums e valores inválidos sem banco. Ingestão valida tudo antes de abrir a transação (falha mostra arquivo e linha).
- **Decisão**: papel `aurora_ro` criado na ingestão (`CREATE/ALTER ROLE` com senha como literal escapado, pois comandos utilitários não aceitam parâmetros); a API só conecta com ele.
- **Decisão**: o canal de entrada não consta em `referencia_ouvidoria.json`; os valores válidos (Portal, E-mail, Telefone, Chat) vêm do dicionário de dados/briefing.
- `RulesLLM`: domínio não reconhecido vira `fora_de_escopo` por enquanto (a decisão por BM25 é da Fase 3); mais de um domínio com palavras-chave vira `ambigua` com candidatos.
- Testes: `tests/test_ingestion.py`.

### 2026-10-21 — T016–T025 API, ouvidoria, frontend, rastreio
- `main.py` (middleware de `trace_id`, `POST /ask`, `GET /traces/{id}`, `/health`, estáticos), `queries/ouvidoria.py`, `agents/ouvidoria.py`, `orchestrator.py` (grafo LangGraph: `guard → classificar → agente_ouvidoria | indisponivel | esclarecer | fora_de_escopo`), `frontend/`, `README.md` (rascunho).
- **Decisão**: o nó `guard` existe mas `guards.recusa` retorna `None` até a Fase 4 (AV-T010), para manter o formato do grafo previsto no plano.
- **Decisão**: protocolo com formato inválido (`OUV-12`, `OUV-00023`) pede esclarecimento; só `OUV-\d{4}` chega à consulta, em maiúsculas.
- **Decisão**: financeiro e informações internas respondem "agente ainda não disponível" (`status=erro`) em vez de inventar resposta.
- Testes: `tests/test_tracing.py`, `test_ouvidoria_protocolo.py` (AV-T009, AV-T004, formato inválido, tentativa de injeção de SQL), `test_api.py` (422, `/health`, 502 sem banco, frontend, classificação por regras).

### 2026-10-21 — T026 Verificação no Docker
- Docker iniciado pelo usuário. `docker compose up --build` subiu `db` (saudável) e `app`; a ingestão rodou na subida (300/144/180).
- **Problema**: a porta 8000 do host estava ocupada por outro projeto (`rag_project-api-1`). **Solução**: porta publicada configurável, `APP_PORT` (padrão 8000, documentada no `.env.example`); o `.env` local usa 8010. O contêiner alheio não foi alterado.
- Verificado nos contêineres: reingestão duas vezes sem duplicar; `docker compose run --rm app pytest` → 34 passados; AV-T009 e AV-T004 por HTTP; `/traces/{id}`; log persistido no volume; processo roda como `appuser`; com o `db` parado, `/ask` dá 502 claro e `/health` responde `banco: indisponivel`; ao religar o `db`, a API volta a responder sem reiniciar.

### 2026-10-21 — Clarify, sessão 2 (sessão `d859bda9…`; entre a Fase 1 e a Fase 2)
- Nova varredura de ambiguidades da spec; 3 lacunas que afetam a Fase 2, todas respondidas na opção recomendada pela IA:
  - Pergunta financeira sem período → **pedir o período** (FR-035).
  - "Receita líquida": a base não tem deduções (17 receitas, todas "Receita de serviços") → **total de receitas, declarando a ausência de deduções** (FR-036).
  - Listas → **10 itens + total** (FR-010).
- Aplicado em `spec.md`, `research.md` e `tasks.md` (T028, T029, T030, T034, T035). Nenhum código alterado.

### Resumo da Fase 1 (gate concluído; falta o commit da fase)
- **Objetivo**: ambiente executável com ingestão, `/ask`, ouvidoria por protocolo, frontend e rastreio.
- **O que funciona (verificado)**: ingestão de 300/144/180 linhas e idempotente (executada duas vezes); papel `aurora_ro` lê e não escreve; AV-T009 e AV-T004 pela API real (uvicorn + curl); `trace_id` no cabeçalho, no corpo e em `/traces/{id}`; 422 para entrada inválida; 502 claro sem banco, com API ativa; frontend servido.
- **Testes**: `pytest` 34 passados no contêiner e com PostgreSQL local; sem banco, 20 passados e 14 ignorados.
- **Docker**: `Dockerfile`, `docker-compose.yml` e `scripts/start.sh` verificados em execução real (ver nota T026).
- **Frontend**: verificado pelo usuário no navegador (localhost:8010) com a pergunta "Qual o status do protocolo OUV-0002?"; o aviso "Modo degradado: roteamento por regras, sem LLM." aparece, como esperado sem chave. A IA não tem navegador neste ambiente; o relato é do usuário.
- **Limitações**: só ouvidoria por protocolo; o classificador por regras é simples.
- **Pendências**: commit da fase (usuário) e aprovação explícita para a Fase 2.

### 2026-10-21 — Decisão: guardrail de prompt injection/jailbreak (planejamento, sem código)
- **Pergunta do autor**: incluir um classificador de prompt injection/jailbreak no RAG, pensando nos testes do avaliador, ou deixar como "a implementar"?
- **Sugestão da IA (aceita)**: não usar classificador por modelo (Prompt Guard, Llama Guard, LLM como juiz). Ele quebraria o modo sem chave ou traria dependência pesada e latência, iria contra o princípio IV e nenhum AV-T exige isso. A arquitetura já limita o estrago: consultas fixas com papel `ro`, números e fontes escritos por código, saída do LLM validada por schema. O ponto exposto é o texto livre da resposta de informações internas.
- **Decisão**: camada determinística na Fase 4 (T049a: `detectar_injecao` por regex na pergunta e na indexação; T051a: testes, incluindo falsos positivos). Trechos delimitados como dados já estavam previstos (T048). O classificador dedicado fica documentado no README como trabalho futuro (T059).

---

## Fase 2 — Ouvidoria completa e Financeiro

> Notas escritas no fim da implementação da fase, na sessão `d859bda9…`.

### 2026-10-21 — T027–T028 Ouvidoria por filtros
- `queries/ouvidoria.py`: `contar`, `listar` (no máximo 10 + total, ordem por abertura e protocolo) e `carregar_referencia`; filtros por whitelist de colunas.
- `agents/ouvidoria.py` reescrito: despacha `buscar_protocolo`, `referencia`, `contar`, `listar`; valor fora da base de referência vira esclarecimento listando os válidos. `Resultado` foi movido para `agents/base.py` e ganhou `dados` (valores calculados, usados nos testes e não expostos pela API).
- **Decisão**: `canal` não consta no JSON de referência; os canais válidos vêm do dicionário de dados e a fonte da resposta é `dicionario_de_dados.md`.

### 2026-10-21 — T029–T031 Financeiro e regras
- `queries/financeiro.py`: `ParamsFinanceiro` (Pydantic, `extra="forbid"`), somas por tipo/status/data, orçamento total e por departamento; colunas por whitelist, valores por `%s`, `Decimal`.
- `agents/financeiro.py`: critério declarado em toda resposta; gasto sem critério → incorrida com aviso (FR-017); período ausente → esclarecimento (FR-035); `receita_liquida` = receitas com aviso de ausência de deduções (FR-036); ano fora de 2025–2026 → "não encontrado"; departamento validado contra o banco.
- **Decisão (interpretação minha)**: *execução orçamentária* usa despesas **pagas** por padrão, porque `indicadores_e_regras.json` define o indicador como "despesas realizadas ÷ orçamento" e realizadas = pagas; difere do padrão "incorrida" de FR-017, que vale para perguntas de "gasto". A resposta declara a escolha.
- **Decisão**: inadimplência calculada em **valor** (atrasadas ÷ total de receitas), declarado na resposta; a definição do JSON não diz valor ou quantidade.
- `llm/rules.py`: extração por regex de período (mês, intervalo, trimestre, semestre), tipo de consulta, critério pago/incorrido, vencimento, centro de custo e departamento. "Financeiro" como departamento só vale após "departamento/área/setor", pois também é o nome do domínio.
- `periodo.py`: conversão de texto em intervalos [início, fim).

### 2026-10-21 — T032 Orquestrador
- Nó `agente_financeiro`; `montar_grafo` recebe `data_dir` para carregar a referência de ouvidoria. Palavras-chave passaram a casar por prefixo (plural e flexões: "receitas", "gastamos").
- **Decisão**: categorias de ouvidoria que também são assuntos de políticas ("reembolso", "privacidade") não geram ambiguidade quando a pergunta já tem palavra forte de ouvidoria ("manifestações", "protocolo"). Cruzamentos reais (ex.: despesa + reembolso, manifestações + despesas) continuam gerando esclarecimento (FR-005).

### 2026-10-21 — T033–T036 Testes
- `tests/oracle.py` calcula tudo de novo em `csv` + `Decimal`, sem usar o código da aplicação. `test_financeiro.py`, `test_ouvidoria_filtros.py`, `test_routing_multidominio.py`, `test_periodo.py`: 47 testes novos.
- **Bug achado pelos testes**: "foram abertas em janeiro de 2026" era lido como status *Aberto* em vez de data de abertura. **Correção**: o padrão do status ignora "aberta(s)" seguida de preposição + data; há teste dos dois sentidos.
- **Bug achado pelos testes**: "Quanto gastamos em 2024?" caía em fora de escopo, pois a lista tinha só "gasto"; trocado pela raiz "gast".

### Resumo da Fase 2
- **Objetivo**: AV-T005, AV-T006, AV-T007 e AV-T011 por código determinístico, com critério declarado.
- **O que funciona (verificado)**: AV-T005 (lista exatamente os 5 status do JSON); AV-T006 (R$ 305.937,01, 27 lançamentos), AV-T007 (Tecnologia, R$ 43.229,05) e AV-T011 (R$ 275.727,70) iguais ao oráculo independente, centavo a centavo; contagens e listas de ouvidoria iguais ao oráculo; listas limitadas a 10 com o total; período ausente pede esclarecimento; perguntas que cruzam domínios pedem esclarecimento.
- **Testes**: `pytest` 81 passados no contêiner e com PostgreSQL local, sem rede; `ruff` (erros e imports não usados) limpo. Perguntas reais por HTTP no Docker conferidas.
- **Limitações**: a extração de parâmetros por regras é simples (categoria de lançamento não é extraída; comparação só entre dois anos; períodos relativos como "mês passado" não são entendidos); sem LLM, perguntas fora desses padrões caem em esclarecimento. AV-T001–T003, T008 e T012 (informações internas) e AV-T010 (recusa) ficam para as Fases 3 e 4.
- **Pendências**: aprovação para a Fase 3 (commit feito: `6fe999e`).

---

## Entre as Fases 2 e 3 — `/speckit-analyze` e correções

### 2026-10-21 — Análise de consistência
- `/speckit-analyze` (só leitura, já com Opus 5.5): 1 crítico, 1 alto, 4 médios e 9 baixos; cobertura dos FR 100%.
- **Crítico (C1), desvio de processo meu**: nas Fases 1 e 2 as notas do DEVLOG foram escritas em bloco no fim de cada fase, e as tarefas marcadas `[X]` também em bloco. O princípio VI pede uma nota a cada tarefa, durante o desenvolvimento. As notas passadas **não** foram reescritas para parecer contínuas. **Correção a partir da Fase 3**: nota no DEVLOG logo após cada tarefa, antes do `[X]`.
- **Alto (I1)**: `contracts/llm-schemas.md` e `data-model.md` não tinham os parâmetros que o código já aceita (`receita_liquida`, comparação, `ordem`, `referencia_tipo`); o schema do Gemini (T045) sairia incompleto. Atualizados.
- **Médios**: seção "Decisões em aberto" da spec desatualizada → substituída (T064 concluída); decisões de execução orçamentária (pagas) e inadimplência (valor) só existiam no DEVLOG → viraram FR-037 e FR-038; SC-007 sem medição → T056 calcula o p90; exportação de conversas por fase não feita → **decisão**: exportação única na T065, porque a sessão atravessa várias fases (CLAUDE.md, `docs/conversas/README.md` e `tasks.md` ajustados).
- **Baixos aplicados**: T004 anota o desvio de dependências; T038/T045 incluem as dependências adiadas; `quickstart.md` cita `APP_PORT`; árvore do `plan.md` com `periodo.py` e `agents/base.py`; T062 cita a pergunta no log como limitação; T067 roda o `pytest` 3 vezes (SC-008); spec com Clarifications depois do cabeçalho e status "Clarified".
- **Não aplicado (A1)**: a constituição V diz "pytest sem rede", e os testes usam o PostgreSQL pela rede interna do Docker. A intenção (sem LLM nem serviços externos) é cumprida; esclarecer o texto exige emenda PATCH, fica como sugestão.
- **Observação**: as tarefas T049a e T051a (detecção de prompt injection por regex) foram adicionadas ao `tasks.md` fora desta sessão e entraram no commit da Fase 2 junto com o arquivo.

