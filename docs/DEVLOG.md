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

_(aguardando início)_
