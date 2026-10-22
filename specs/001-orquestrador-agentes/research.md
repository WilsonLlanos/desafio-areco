# Research — Orquestrador de Agentes (Aurora)

Resolve as decisões da seção 8 do briefing ainda abertas após o clarify (2, 3 e 6) e detalha as escolhas técnicas do plano. As decisões 1, 4 e 5 estão em `spec.md` (Clarifications).

## 1. Estratégia de recuperação (RAG) — decisão 2
- **Decisão**: BM25 em memória (`rank-bm25`) sobre chunks por seção/documento, com metadados `domain`, `source`, `document_version`. Índice reconstruído na subida da API a partir de `data/informacoes_internas/`.
- **Rationale**: corpus de ~8,5 KB e 17 itens; funciona **sem chave** (exigência do modo degradado) e sem rede nos testes; zero serviço/extensão novo.
- **Alternativas**: pgvector (exige embeddings via API, quebra o modo sem chave, extensão extra); FAISS (dependência sem ganho neste tamanho).
- **Detalhes**: tokenização minúscula, sem acentos, stopwords PT básicas; FAQ indexado como item próprio apontando para o campo `documento`; recupera top-3 e descarta abaixo de um escore mínimo (→ "não encontrei na base"). `document_version` extraído do texto do documento, se existir; senão `n/d`.

## 2. Framework de agentes — decisão 3
- **Decisão**: **LangGraph** (`langgraph`) para o grafo de orquestração, por escolha do autor; as regras do desafio permitem frameworks. Nós: `guard → classify → (esclarecer | fora_de_escopo | agente_X) → finalizar`, com arestas condicionais pelo domínio/confiança. Estado tipado (`TypedDict`) carrega `trace_id`, pergunta, classificação, fontes e resposta.
- **Rationale**: grafo explícito e visualizável (`get_graph().draw_mermaid()` vai para a documentação), roteamento condicional nativo, fácil de estender.
- **Limites (constituição II e IV)**: LangGraph só orquestra; os nós continuam chamando o `LLMClient` próprio e as consultas parametrizadas. **Sem `create_react_agent`/tool-calling livre**: o LLM não escolhe ferramentas nem gera SQL. Usar `langchain-google-genai` somente se necessário; padrão é manter `google-genai` direto atrás do `LLMClient`.
- **Testes**: o grafo compila com `FakeLLM` injetado; sem rede.
- **Alternativas**: implementação própria (recomendada no briefing, mais enxuta); LangChain puro (sem grafo explícito).

## 3. Formato das fontes — decisão 6
- **Decisão**: lista de objetos `{tipo, ref, detalhe}`:
  - informações internas: `{arquivo, "01_politica_ferias.md", seção/FAQ-id}`
  - ouvidoria: `{protocolo, "OUV-0002"}` ou, em agregados, `{consulta, "ouvidoria.contar_por_status", filtros}` + `manifestacoes.csv`
  - financeiro: `{consulta, "financeiro.soma_despesas", critério}` + arquivo base, e até 10 IDs `FIN-xxxx` mais a contagem total.
- **Rationale**: rastreável e verificável sem inflar a resposta.

## 4. Provedor de LLM
- **Decisão**: Gemini via SDK `google-genai`, modelo em `GEMINI_MODEL` (padrão `gemini-3.1-flash-lite`, escolhido pelo autor; validar o id e o suporte a saída estruturada na Fase 4). Saída estruturada com `response_schema` para classificação e parâmetros. Interface `LLMClient` injetável; `FakeLLM` nos testes; `RulesLLM` quando `GEMINI_API_KEY` ausente.
- **Degradação sem chave**: roteamento por palavras-chave/regex (protocolo `OUV-\d{4}`, termos financeiros, termos de ouvidoria, caso contrário BM25 decide entre internas e fora de escopo por escore) e extração de parâmetros por regex; resposta de internas extrativa; a API inclui `modo: "degradado"` e a UI exibe aviso (FR-034).
- **Falha em tempo de execução** (timeout/erro do provedor): uma tentativa com timeout de 8 s; falhou → cai para regras na classificação e devolve erro claro se a redação for indispensável; sempre registra no log.

## 5. Classificação e confiança
- Saída: `{dominio, confianca[0..1], dominios_candidatos[]}`. Limiar `0.6` configurável.
- `dominio=ambigua` ou `confianca<limiar` ou ≥2 candidatos acima de `0.5` → pedido de esclarecimento (FR-003/FR-005, sem combinar agentes).
- Pergunta fora de escopo → explicação de escopo (FR-004).

## 6. Consultas parametrizadas (financeiro e ouvidoria)
- **Catálogo fixo** com parâmetros tipados (Pydantic): período (`ano`, `mes`, intervalo), `tipo_data` (`competencia`|`vencimento`, padrão competência), `criterio_gasto` (`paga`|`incorrida`, padrão **incorrida**), `status`, `departamento`, `centro_custo` (CC100–CC600), `categoria`, `prioridade`, `canal`, `protocolo` (`^OUV-\d{4}$`, normalizado para maiúsculas).
- Financeiro: `soma_despesas`, `soma_receitas`, `comparar_periodos`, `orcamento_por_departamento` (maior/menor), `execucao_orcamentaria`, `inadimplencia`. Ouvidoria: `buscar_protocolo`, `listar/contar` com filtros, `referencia` (enums de `referencia_ouvidoria.json`).
- **Período ausente** em pergunta financeira → esclarecimento (FR-035). **`receita_liquida`**: soma das receitas, declarando que não há deduções registradas (FR-036). **Listas** (ouvidoria): até 10 itens mais o total (FR-010). **Execução orçamentária**: despesas pagas por padrão, pois o indicador é "despesas realizadas ÷ orçamento" (FR-037). **Inadimplência**: em valor (FR-038). **Comparação**: dois períodos, métrica receitas ou despesas. **Orçamento por departamento**: ranking com `ordem` maior/menor e empates.
- SQL com `%s`/`NUMERIC`, nomes de coluna vindos de whitelist no código. Resposta renderizada por **template em código** com critério declarado; o LLM não vê nem escreve números.
- Parâmetro ausente que muda o resultado (ex.: período) → esclarecimento; "gasto" sem critério → incorrida, declarado (FR-017).
- Ano fora de 2025–2026 ou sem lançamentos → resposta explícita "sem dados no período".

## 7. Segurança (skill `llm-safety-hardening`)
- Papel Postgres `aurora_ro` com `SELECT` apenas; a API usa só ele. Ingestão usa o papel dono.
- Guarda pré-LLM (`guards.py`): padrões de credenciais/senhas/dados de terceiros, pedidos de holerite/saldo individual → recusa/encaminhamento (AV-T010, FR-007, FR-028). Entrada vazia, só símbolos ou > 1.000 caracteres → rejeitada (FR-027).
- Chunks e pergunta enviados como dados delimitados; fontes não vêm do texto do modelo; resposta de internas descartada se citar fonte fora dos trechos.
- **Detecção de prompt injection por padrões** (`guards.detectar_injecao`, regex PT/EN sobre texto normalizado): criada na Fase 3 (T038) para a **injeção indireta** — trecho de documento que casar é registrado e não é indexado — e reaproveitada na Fase 4 (T049a) para a **injeção direta** — pergunta que casar é recusada com explicação de escopo antes do LLM (FR-029). É uma camada **complementar e contornável** (ofuscação, outros idiomas, base64); não substitui as defesas estruturais acima. No corpus atual o risco indireto é baixo (documentos fixos e imutáveis, FR-023); o filtro existe para tratar conteúdo recuperado como não confiável (constituição VIII).
- Smoke test adversarial informal na Fase 4; reportar como spot-check, não auditoria.

## 8. Ingestão idempotente
- `python -m app.ingestion` na subida do `app`: aplica `data/sql/schema.sql`, lê CSV com `utf-8-sig`, valida datas e enums contra `referencia_ouvidoria.json`/`schema.sql`, converte `valor_brl` para `Decimal`, `INSERT … ON CONFLICT DO UPDATE` por chave primária; cria o papel `aurora_ro` e concede `SELECT`. Rodar duas vezes não duplica (FR-022). `data/` montado como somente leitura.

## 9. Rastreabilidade
- Middleware cria `trace_id` (UUID4) → `contextvar`; resposta devolve o id também no cabeçalho `X-Trace-Id`. Log JSON por requisição em stdout e em `logs/interactions.jsonl` (volume). `GET /traces/{trace_id}` lê o JSONL. Campos: ver `data-model.md`. Pergunta é registrada (exigência da constituição); sem segredos.

## 10. Frontend
- HTML/CSS/JS puros em `frontend/`, servidos por `StaticFiles`. Mostra carregando, erro, resposta, domínio, agente, confiança, fontes, `trace_id`, aviso de modo degradado. Sem memória de conversa (suposição do spec: desejável, não obrigatória).

## 11. Avaliação
- `scripts/evaluate.py`: lê `perguntas_avaliacao.json`, chama `POST /ask` (ou o orquestrador) com Gemini real, verifica domínio (T010 aceita `fora_de_escopo_ou_segurança` → recusa), fonte esperada ∈ fontes retornadas e conteúdo-chave por asserções por caso; grava `docs/evaluation/avaliacao-<data>.jsonl`. Valores de AV-T006/T007/T011 comparados a cálculo independente em Python puro sobre os CSV (SC-003).

## 12. Juiz de avaliação (FR-039)
- **Decisão**: juiz LLM **complementar**, só em `scripts/evaluate.py` (via `scripts/judge.py`), com modelo Gemini Pro definido em `JUDGE_MODEL`. Aprovado/reprovado continua determinístico; o juiz registra nota, justificativa e `divergente` (`contracts/judge.md`).
- **Rationale (escolha do usuário)**: mesma chave e mesmo SDK `google-genai` já previstos, sem dependência nova; o juiz só troca de modelo, não de provedor.
- **Alternativa descartada**: juiz de outra família (sugestão da IA: Claude), que reduz o viés de autoavaliação mas exige outra chave e outro SDK. Fica como **melhoria futura**.
- **Limitação e mitigação**: viés favorável de mesma família. Mitigado com referência explícita por caso (documento esperado, valor do oráculo, registro de ouvidoria), rubrica fixa, temperatura 0 e decisão final determinística. Será documentado em `docs/limitacoes.md` (T062).
- **Quando**: implementado com a T056, na Fase 5.

