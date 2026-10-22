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

### 2026-10-21 — Decisão: juiz LLM na avaliação (FR-039)
- **Pedido do usuário**: um juiz (modelo superior) avaliando as respostas só na suíte AV-T001–T012, sem entrar na aplicação.
- **Sugestão da IA (descartada)**: juiz de outra família (Claude Opus 5.5), para reduzir o viés de um modelo avaliar bem a própria família.
- **Decisão do usuário**: Gemini Pro em `JUDGE_MODEL` (mesmo provedor e mesma chave, outro modelo), **complementar** (as checagens determinísticas continuam decidindo aprovado/reprovado; o juiz dá nota, justificativa e sinaliza divergência), implementado com a T056 na Fase 5. Juiz de outra família fica como melhoria futura.
- **Mitigação do viés**: referência explícita por caso, rubrica fixa, temperatura 0, decisão final determinística.
- Artefatos: FR-039 e Clarifications na spec, `research.md` §12, `contracts/judge.md` (novo), `data-model.md`, `plan.md`, T056a/T056b (e T061/T062) em `tasks.md`, `JUDGE_MODEL` no `.env.example`. Nenhum código alterado.

### 2026-10-21 — `/speckit-analyze` (2ª execução) e correções
- Resultado: nenhum crítico ou alto; 2 médios, 3 baixos; cobertura de FR e SC 100%.
- **Dúvida do usuário**: "a instrução embutida seria o prompt injection?" Sim, na variante **indireta** (instrução escondida no conteúdo recuperado pelo RAG); a direta vem na própria pergunta. No corpus atual o risco indireto é baixo (documentos fixos e imutáveis), mas a constituição VIII manda tratar conteúdo recuperado como não confiável.
- **I4 (médio)**: o filtro de injeção na indexação estava na T049a (Fase 4), mas o índice nasce na T038 (Fase 3). **Decisão do usuário**: `detectar_injecao` é criada na T038 e usada na indexação; a T049a a reaproveita para a pergunta. Teste do filtro de indexação movido da T051a para a nova T043a.
- **U2 (médio)**: spec e plano não diziam o que fazer ao detectar injeção. **Decisão do usuário**: detecção na pergunta → **recusa** com explicação de escopo antes do LLM; trecho de documento → não indexado (FR-029, Clarifications, `research.md` §7, `plan.md`). Documentado que a regex é camada complementar e contornável; a proteção principal é estrutural.
- **Baixos**: T056b deixa de ser `[P]` (depende da T056a); juiz citado no `plan.md` e no `quickstart.md`; **emenda 1.2.1 da constituição** (PATCH, princípio V): "sem rede" passa a ser "sem rede externa nem LLM real", com PostgreSQL local/do compose permitido.

---

## Fase 3 — Informações internas (RAG)

> A partir desta fase, uma nota por tarefa, escrita logo após a tarefa e antes do `[X]` (correção do achado C1).

### 2026-10-21 — T038 Índice RAG e `detectar_injecao`
- `app/texto.py` (normalização, stopwords PT, radical de 5 letras), `app/rag/index.py` (17 itens: 10 documentos inteiros + 7 do FAQ; metadados `domain`, `source`, `secao`, `document_version` extraída de "Versão X — data") e `guards.detectar_injecao` (regex PT/EN). Item com padrão de injeção é logado e não indexado.
- **Desvio do plano**: BM25 implementado à mão (~25 linhas) em vez de `rank-bm25`, que traria `numpy` para 17 itens; `requirements.txt` sem dependência nova.
- **Decisão**: um item por documento (os documentos têm ~500–850 bytes, como o briefing indica), não por seção; o FAQ vira itens próprios, citando o `documento` de origem.
- **Teste manual**: AV-T001 → FAQ-001 (doc 01), AV-T002 → FAQ-003 (02), AV-T003 → doc 03, AV-T008 → FAQ-005 (04), AV-T012 → doc 07; "previsão do tempo" e "capital da França" sem resultado; nenhum dos 17 itens reais casou com o filtro de injeção. Limitação observada: "quais as instruções para pedir reembolso?" traz primeiro o FAQ de acesso (termo "pedir"); a resposta ainda cita reembolso entre os 3 primeiros.

### 2026-10-21 — T039 Agente de informações internas (extrativo)
- `app/agents/internal.py`: busca no índice; escore abaixo de 2,0 → "não encontrei" (`nao_encontrado`), sem inventar. Resposta: (1) se a pergunta tem valor em R$, a linha da faixa de alçada correspondente ("Até", "De … a …", "Acima de"); (2) se o melhor item é do FAQ, a resposta do FAQ; (3) senão, até 2 linhas do documento com mais termos em comum e 1 linha de proibição ("Não…/Nunca…") como "Atenção". Linhas da seção "Limites do agente" e frases sobre "o agente" ficam fora da resposta ao usuário.
- Fonte definida por código: arquivo de origem + seção ou id do FAQ + versão do documento.
- **Decisão**: a faixa de valor tem prioridade sobre o FAQ, porque o FAQ-004 só cobre "acima de R$ 10.000"; perguntar por R$ 5.000 com a resposta do FAQ estaria errado.
- **Teste manual**: AV-T001, T002, T003, T008 e T012 com o conteúdo-chave do critério e a fonte esperada; R$ 2.000 (limite) → "Até R$ 2.000", R$ 5.000,00 → faixa intermediária; "capital da França" → não encontrado. Ajuste de código: regex de faixa simplificadas (constante para texto normalizado).

### 2026-10-21 — T040 Limites dos documentos (FR-007)
- `internal.limite()` roda antes da busca e devolve encaminhamento com `status=recusado` e fonte do documento que define o limite: dados de outros colaboradores/clientes → `09_politica_privacidade.md` e privacidade@; saldo individual de férias → `01_politica_ferias.md` e RH; holerite/salário próprio → `08_faq_rh.md` e RH; caso trabalhista → `01_politica_ferias.md` e RH.
- **Decisão**: dados de terceiros é checado primeiro ("férias do colega" é dado de terceiro, não saldo próprio). Pedido de **senha** de terceiro (AV-T010) não entra aqui: é a guarda de credenciais da Fase 4 (T049).
- **Teste manual**: 6 pedidos individuais recusados com o canal certo; "Como solicito férias?" e "Quais dados pessoais posso usar em testes?" seguem respondidos normalmente (sem falso positivo).

### 2026-10-21 — T041 Orquestrador com o agente de informações internas
- Nó `agente_internas` no grafo (substitui o nó provisório `indisponivel` da Fase 1); o índice é criado uma vez em `create_app` e compartilhado pelo grafo e pelo `RulesLLM`. `ESCORE_MINIMO` passou para `app/rag/index.py` (usado pelo agente e pelas regras).
- `RulesLLM`: sem palavra-chave de nenhum domínio, o escore do BM25 ≥ 2,0 classifica como informações internas (confiança 0,7); abaixo disso, fora de escopo. Palavras-chave novas de internas: holerite, contracheque, trabalhista, rescisão.
- Teste da Fase 1 `test_dominio_sem_agente_responde_indisponivel` reescrito como `test_informacoes_internas_respondem_sem_banco` (o agente agora existe e não depende do banco).
- **Verificação pela API (modo degradado)**: os 12 casos AV com o domínio esperado; 11 com a fonte esperada. **AV-T010** ("senha de outro colaborador") cai em `fora_de_escopo` sem orientar o canal autorizado: a recusa com orientação é da Fase 4 (T049). `pytest` 81 passados, `ruff` limpo.

### 2026-10-21 — T042 Testes do RAG
- `tests/test_rag.py` (20 testes): índice com 17 itens e metadados; FAQ aponta para o documento; AV-T001, T002, T003, T008 e T012 com fonte exata e conteúdo-chave do critério; alçada de compra nos limites das faixas (R$ 2.000, 2.000,01, 10.000, 10.000,01); tudo o que a resposta afirma é texto do documento/FAQ (FR-008); fonte com seção e versão; perguntas sem relação → `nao_encontrado` sem fonte; linhas de "Limites do agente" fora da resposta; pela API (sem banco), domínio, agente e fonte.
- **Bug achado pelo teste**: "Me conte uma piada" respondia com o procedimento financeiro, porque o radical de 5 letras igualava "conte" (contar) e "contem" (conter). **Correção**: radical de 6 letras; os escores das perguntas AV quase não mudaram e todas continuam acima do mínimo.
- `pytest` 101 passados.

### 2026-10-21 — T043 Testes dos limites e de "não inventar"
- `tests/test_internal_limits.py` (16 testes): 8 pedidos individuais recusados com o canal e a fonte certos (RH ou privacidade@); perguntas gerais sobre férias, testes e benefícios não bloqueadas; o limite vem antes da busca; perguntas sem resposta na base → "não encontrei"; pela API, holerite → internas, recusado.
- **Bugs achados pelos testes**: (1) "férias da minha colega" não era tratado como dado de terceiro (o padrão não aceitava "minha" entre "da" e "colega") → padrão ampliado; (2) "política de viagens internacionais" respondia com a política de férias, só por "política" e por "internacionais"/"interno" terem o mesmo radical → palavras genéricas da base (política, documento, procedimento, interno, empresa…) viraram stopwords.
- **Efeito colateral corrigido**: "Qual a política de home office?" ficou sem resposta, porque o documento 06 só tem "home office" no nome do arquivo → o nome do arquivo passou a entrar nos termos indexados (metadado). Teste de regressão em `test_rag.py`.
- `pytest` 119 passados.

### 2026-10-21 — T043a Testes do filtro de injeção no RAG
- `tests/test_injecao_rag.py` (20 testes): 12 padrões detectados (PT/EN, maiúsculas, acentos, marcadores de papel); 5 perguntas legítimas com "instruções", "regras", "sistema" não detectadas; nenhum documento real casa; documento com linha injetada (cópia de `data/` em diretório temporário) é logado e não indexado, os outros 16 itens continuam; a instrução plantada não aparece na resposta.
- **Consequência registrada (trade-off)**: como o índice tem um item por documento, uma linha injetada tira o documento inteiro do índice (o FAQ que aponta para ele continua respondendo). Com documentos de ~600 bytes e corpus imutável, é aceitável; num corpus editável, o filtro deveria remover só a linha. Passaram de primeira; nenhum código alterado nesta tarefa.

### 2026-10-21 — T044 Gate da Fase 3
- `docker compose up --build`: `app` sobe com o índice; `docker compose run --rm app pytest` → **139 passados**; `ruff` limpo; perguntas reais por HTTP conferidas (férias, alçada R$ 12.000, incidente, holerite recusado, fora de escopo). Limpeza: `rules.py` passou a usar `normalizar` de `app/texto.py` (havia duas cópias). README com o estado da Fase 3. Diff sem segredos.

### Resumo da Fase 3
- **Objetivo**: AV-T001, T002, T003, T008 e T012 respondidos só com o texto dos documentos, com fonte, funcionando sem chave.
- **O que funciona (verificado)**: índice de 17 itens (10 documentos + 7 do FAQ) com BM25 próprio; os 5 casos AV de informações internas com a fonte esperada e o conteúdo-chave do critério; alçada de compra pela faixa de valor (limites testados); limites dos documentos (saldo, holerite, trabalhista, dados de terceiros) com encaminhamento ao canal certo; "não encontrei" quando a base não tem a resposta; filtro de prompt injection na indexação. Pela API em modo degradado, os 12 casos AV caem no domínio esperado; 11 com a fonte esperada.
- **Decisões técnicas**: BM25 próprio em vez de `rank-bm25` (evita `numpy`); um item por documento; faixa de valor com prioridade sobre o FAQ; stopwords de palavras genéricas da base; nome do arquivo como termo indexado; `ESCORE_MINIMO` 2,0 compartilhado pelo agente e pelo roteamento por regras.
- **Problemas e soluções**: radical de 5 letras colidia ("conte" × "contem") → 6 letras; "política de viagens internacionais" casava com férias → stopwords genéricas; "home office" sumiu → nome do arquivo indexado; "da minha colega" escapava do limite → padrão ampliado.
- **Testes**: 139 passados (58 novos nesta fase), sem rede externa nem LLM.
- **Limitações e pendências**: resposta extrativa (sem redação por LLM até a Fase 4) pode trazer linhas pouco relevantes em perguntas genéricas; radical por truncamento é grosseiro; uma linha injetada remove o documento inteiro do índice. AV-T010 ainda cai em fora de escopo sem orientar o canal autorizado (Fase 4, T049). Commit da fase e aprovação para a Fase 4.
- **Processo**: notas do DEVLOG escritas tarefa a tarefa, antes de cada `[X]` (correção do achado C1).

