# Decisões técnicas

Resumo das decisões e alternativas descartadas. O detalhe está em
`specs/001-orquestrador-agentes/research.md` e o histórico (quem decidiu, quando, o que deu errado) em
`docs/DEVLOG.md`.

## Decisões da seção 8 do briefing

| # | Decisão | Por quê | Alternativas descartadas |
|---|---|---|---|
| 1 | **Google Gemini** `gemini-3.1-flash-lite` (escolha do autor); sem chave, **regras** com aviso | modelo barato e rápido; o sistema precisa funcionar sem chave | sem fallback (quebra sem chave) |
| 2 | **BM25 próprio** em memória sobre 10 documentos + 7 itens do FAQ | 17 itens; funciona sem chave e sem rede; ~30 linhas testadas | `rank-bm25` (traria `numpy`, ~57 MB, sem ganho); pgvector e embeddings (exigem API, quebram o modo sem chave) |
| 3 | **LangGraph** só para o grafo de orquestração (escolha do autor) | grafo explícito, roteamento condicional, diagrama gerado | implementação própria (recomendada no briefing, descartada pelo autor); agente ReAct com tool-calling (o LLM escolheria ferramentas) |
| 4 | Pergunta multi-domínio → **pedido de esclarecimento** | não combinar agentes evita respostas mistas sem fonte clara | responder com os dois agentes |
| 5 | "Gasto" sem critério → **despesa incorrida**, sempre declarada | o critério aparece na resposta; o usuário pode pedir "pagas" | despesa paga como padrão |
| 6 | Fontes como `{tipo, ref, detalhe}` (arquivo, protocolo, lançamento, consulta) | verificáveis e escritas por código | texto livre gerado pelo modelo |

## Decisões do clarify e da implementação

- **Período ausente** em pergunta financeira → pedir o período (FR-035). **Receita líquida** = total
  das receitas, declarando que não há deduções na base (FR-036). **Execução orçamentária**: despesas
  pagas como padrão (FR-037). **Inadimplência** em valor (FR-038). **Listas**: até 10 itens + total (FR-010).
- **O LLM nunca escreve SQL nem números**: escolhe uma consulta de um catálogo fixo e extrai parâmetros
  validados por Pydantic (`extra="forbid"`). Valores em `Decimal`/`NUMERIC`. Papel de banco somente leitura.
- **Saída estruturada** via `response_json_schema` (o `response_schema` do SDK recusa
  `additionalProperties`); timeout de 10 s (mínimo da API; o plano previa 8 s); `thinking_level="minimal"`
  (~3 s em vez de ~7 s por chamada).
- **Falha do provedor** → regras/extrativa naquela requisição, marcada `degradado`; depois da 1ª falha a
  requisição não chama mais o provedor (limita a espera).
- **Redação de informações internas**: fontes do código; número fora dos trechos descarta a redação;
  a proibição do documento principal é acrescentada se o modelo a omitir (falha real do AV-T012).
- **Prompt injection**: na pergunta → recusa antes do LLM; em documento → não indexado. Regex é camada
  complementar; as defesas estruturais (consultas fixas, papel `ro`, contratos, fontes por código) vêm antes.
- **Faixa de valor** (alçadas de compra) escolhida por código, sem o modelo.

## Avaliação

- **Determinístico decide** aprovado/reprovado: domínio, fonte esperada, conteúdo-chave do critério e,
  nos casos financeiros, o valor do oráculo calculado direto dos CSV.
- **Resposta degradada não conta como aprovada com LLM**: o script repete até 2 vezes e, se continuar
  degradada, marca `nao_avaliado_llm`.
- **Juiz LLM complementar** (`scripts/judge.py`), só no script: nota, justificativa e divergência; nunca
  reprova. Planejado com Gemini Pro; `gemini-2.5-pro` devolveu 404 e `gemini-3.1-pro-preview` 429 (cota
  do plano gratuito). O autor escolheu **`gemini-3.5-flash`**, mais capaz que o modelo avaliado, mas da
  mesma família. Mitigação do viés: referência explícita por caso, rubrica fixa, temperatura 0 e decisão
  final determinística. Juiz Pro ou de outra família (ex.: Claude) fica como melhoria futura.
- **CI** sem chave do LLM: `pytest` e `docker compose up` a cada push; a avaliação com LLM real fica fora do CI.
