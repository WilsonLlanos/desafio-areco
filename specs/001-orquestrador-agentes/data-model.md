# Data Model

## Persistente (PostgreSQL) — reaproveita `data/sql/schema.sql`

| Tabela | Chave | Observações |
|---|---|---|
| `lancamentos_financeiros` | `id_lancamento` (`FIN-NNNN`) | `tipo` ∈ {Receita, Despesa}; `status` ∈ {Pago, Pendente, Atrasado}; `valor_brl NUMERIC(14,2) ≥ 0`; competência ≠ vencimento |
| `orcamento_mensal` | (`ano`, `mes`, `centro_custo`) | 6 centros (CC100–CC600) × 24 meses; `orcamento_brl NUMERIC(14,2)` |
| `manifestacoes_ouvidoria` | `protocolo` (`OUV-NNNN`) | `status`, `prioridade`, `categoria`, `canal_entrada` validados na ingestão contra `referencia_ouvidoria.json`; `data_resposta` pode ser nula |

Papéis: dono (ingestão: DDL + upsert) e `aurora_ro` (API: `SELECT` nas 3 tabelas). Sem tabelas novas; o log fica em arquivo.

Validações de ingestão: datas ISO; `valor_brl` → `Decimal`; enums; linha inválida aborta a carga com mensagem (arquivo, linha). Estado: carga é upsert, sem transições.

## Em memória (RAG)

**Chunk** — `id`, `texto`, `source` (arquivo `.md` ou `faq_interno.json`), `secao` (título ou `FAQ-00N`), `domain="informacoes_internas"`, `document_version`. Construído na subida; ~17 itens.

## Requisição / resposta (Pydantic)

**AskRequest** — `pergunta: str` (1–1000 caracteres, após `strip`).

**Classificacao** — `dominio` ∈ {financeiro, informacoes_internas, ouvidoria, ambigua, fora_de_escopo}; `confianca: float [0,1]`; `candidatos: list[dominio]`.

**Fonte** — `tipo` ∈ {arquivo, protocolo, lancamento, consulta}; `ref: str`; `detalhe: str | None`.

**AskResponse** — `trace_id`, `resposta`, `dominio`, `agente` (`orquestrador` | `informacoes_internas` | `ouvidoria` | `financeiro`), `confianca`, `fontes: list[Fonte]`, `status` ∈ {ok, nao_encontrado, esclarecimento, fora_de_escopo, recusado, erro}, `modo` ∈ {llm, degradado}, `latencia_ms`.

## Parâmetros extraídos (validados antes de usar)

- **ParamsFinanceiro** (`app/queries/financeiro.py`, `extra="forbid"`): `consulta` (enum do catálogo, inclui `receita_liquida`), `ano`, `mes_inicio`, `mes_fim`, `tipo_data` (padrão `competencia`), `criterio_gasto` (padrão `incorrida`; `paga` na execução orçamentária), `departamento?`, `centro_custo?` (`CC[1-6]00`), `categoria?`, `metrica?`, `ano_b?`, `mes_inicio_b?`, `mes_fim_b?` (comparação), `ordem?` (maior/menor).
- **ParamsOuvidoria**: `consulta` (`buscar_protocolo` | `contar` | `listar` | `referencia`), `protocolo?` (`OUV-NNNN`), `status?`, `categoria?`, `prioridade?`, `canal?`, `data_de?`, `data_ate?` (ISO, exclusivo), `referencia_tipo?`.
- Valor fora do enum/formato → tratado como parâmetro ausente → esclarecimento.

## Registro de interação (JSONL, um objeto por requisição)

`timestamp` (ISO UTC), `trace_id`, `pergunta`, `dominio_previsto`, `confianca`, `agente`, `fontes` (refs/IDs), `latencia_ms`, `status`, `modo`, `erro?` (tipo e mensagem curta). Sem dados pessoais nem segredos.

## Caso de avaliação (resultado por caso no log de avaliação)

`caso_id` (AV-Txxx), `trace_id`, `pergunta`, `dominio_esperado`/`obtido`, `fonte_esperada`/`obtida`, `criterio`, `resultado` (pass/fail + motivo), `latencia_ms`, `juiz_modelo`, `juiz` (`{atende_criterio, fiel_a_referencia, alucinacao, justificativa}` ou `nao_executado`/`erro`), `divergente` (ver `contracts/judge.md`).
