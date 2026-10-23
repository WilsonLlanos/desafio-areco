# Aurora — Orquestrador de Agentes de Perguntas

[![CI](https://github.com/WilsonLlanos/desafio-areco/actions/workflows/ci.yml/badge.svg)](https://github.com/WilsonLlanos/desafio-areco/actions/workflows/ci.yml)

Aplicação web em que um orquestrador (LangGraph) classifica a pergunta e a encaminha ao agente
especializado: **financeiro**, **informações internas** ou **ouvidoria**. Dados sintéticos (empresa
fictícia Aurora). O LLM (Google Gemini) classifica, extrai parâmetros e redige respostas de documentos;
números, consultas e fontes são sempre produzidos por código.

**Estado**: as 5 fases planejadas estão implementadas. Avaliação com LLM real: 12/12 casos aprovados
(`docs/evaluation/`). Limitações e pendências: `docs/limitacoes.md`.

## Pré-requisitos

- Docker e Docker Compose.
- Opcional: chave da API do Google Gemini (sem ela, o sistema funciona por regras, em modo degradado).

## Executar

```bash
cp .env.example .env     # troque as senhas; preencha GEMINI_API_KEY se tiver
docker compose up --build
```

Abra http://localhost:8000. Se a porta estiver ocupada, defina `APP_PORT` no `.env` e use essa porta.
Na subida, o `app` aplica o schema, carrega as bases (pode repetir sem duplicar) e indexa os documentos;
o log mostra `LLM: Gemini (...)` ou `LLM: regras (modo degradado)`.

| Variável | Uso |
|---|---|
| `POSTGRES_*` | banco e usuário dono (ingestão) |
| `DB_RO_USER`, `DB_RO_PASSWORD` | papel somente leitura usado pela API |
| `GEMINI_API_KEY` | chave do Gemini; vazia = modo degradado |
| `GEMINI_MODEL` | padrão `gemini-3.1-flash-lite` |
| `CONFIDENCE_THRESHOLD` | abaixo disso, a API pede esclarecimento (padrão 0,6) |
| `JUDGE_MODEL` | juiz da avaliação (só `scripts/evaluate.py`); vazio = sem juiz |
| `APP_PORT` | porta publicada no host |

Exemplos de perguntas: `Qual o status do protocolo OUV-0002?`, `Quais status podem aparecer na ouvidoria?`,
`Quanto foi gasto em despesas pagas de janeiro a março de 2025?`, `Qual departamento tem maior orçamento em janeiro de 2026?`,
`Como solicito férias?`, `Quais são as aprovações para uma compra de R$ 12.000?`.

```bash
curl -s localhost:8000/ask -H 'content-type: application/json' \
  -d '{"pergunta":"Qual o status do protocolo OUV-0002?"}'
curl -s localhost:8000/traces/<trace_id>     # registro da interação
curl -s localhost:8000/health                # banco e modo (llm | degradado)
```

A resposta traz `resposta`, `dominio`, `agente`, `confianca`, `fontes`, `status`, `modo`,
`latencia_ms` e `trace_id`. `modo: "degradado"` indica que aquela resposta saiu por regras (sem chave
ou falha do provedor); o frontend mostra um aviso.

## Testes

```bash
docker compose run --rm app pytest      # 241 testes: lógica, LLM falso, sem rede
```

Avaliação AV-T001–AV-T012 com o LLM real (requer `GEMINI_API_KEY`; `JUDGE_MODEL` opcional):

```bash
docker compose up -d
docker compose run --rm -v "$PWD/docs/evaluation:/app/docs/evaluation" -e JUDGE_MODEL=gemini-3.5-flash \
  app python scripts/evaluate.py --url http://app:8000
```

Gera `docs/evaluation/avaliacao-<data-hora>.jsonl` (um registro por caso + resumo) e
`interacoes-amostra.jsonl`. Aprovado/reprovado é decidido por checagens determinísticas (valores
financeiros contra cálculo direto dos CSV); resposta degradada é repetida e, se continuar, conta como
"não avaliada com LLM". O juiz só registra nota, justificativa e divergência.

## Integração contínua

`.github/workflows/ci.yml` roda em todo push e pull request, **sem chave do LLM**:
- lint (`ruff`) e `pytest` com um PostgreSQL 16 de serviço;
- `docker compose up --build`, `/health`, perguntas de fumaça (AV-T009 e AV-T010) e `pytest` dentro do contêiner.

A avaliação com LLM real não roda no CI (exige chave e custa chamadas).

## Segurança

Camadas, da mais forte para a mais fraca:
1. **Estruturais**: consultas SQL fixas e parametrizadas, executadas por um papel que só tem `SELECT`;
   o LLM escolhe uma consulta de um catálogo e extrai parâmetros validados (`extra="forbid"`); números e
   fontes escritos por código; redação descartada se citar fonte ou número fora dos trechos.
2. **Guardas pré-LLM** (`app/guards.py`): pedido de credencial, dados de terceiros e padrões de prompt
   injection são recusados antes de qualquer chamada ao modelo; documento com instrução embutida não é indexado.
3. **Instruções ao modelo**: pergunta e trechos delimitados como dados; ordens contidas neles devem ser ignoradas.

Limitações: as guardas são regex em português (e inglês para injeção) e não cobrem paráfrase,
outros idiomas ou ofuscação. A implementar: classificador dedicado (ex.: Prompt Guard), conjunto
adversarial maior. Detalhes em `docs/limitacoes.md`.

## Solução de problemas

| Sintoma | Causa provável |
|---|---|
| `port is already allocated` | porta 8000 ocupada: defina `APP_PORT` no `.env` |
| `/health` com `"banco": "indisponivel"` | `db` ainda subindo ou senha diferente no `.env` |
| todas as respostas `degradado` com chave | provedor sobrecarregado (503/504) ou cota; veja `docker compose logs app \| grep "falha do provedor"` |
| avaliação com muitos `nao_avaliado_llm` | mesmo motivo; no plano gratuito o Gemini falhou com frequência, no nível 1 não |

## Estrutura

```
app/            API, orquestrador (LangGraph), agentes, consultas, LLM, RAG, ingestão, rastreio
frontend/       chat em HTML/CSS/JS
scripts/        start.sh, evaluate.py (avaliação), judge.py (juiz)
tests/          pytest (+ oracle.py: cálculo independente sobre os CSV)
data/           bases fornecidas (somente leitura)
specs/          spec, plano, pesquisa, contratos e tarefas (Spec Kit)
docs/           arquitetura, decisões, limitações, DEVLOG, avaliação, histórico das conversas
```

## Documentação

- `docs/arquitetura.md`: componentes, grafo, fluxo de dados, papéis de banco, logs.
- `docs/decisoes.md`: decisões técnicas e alternativas descartadas.
- `docs/limitacoes.md`: limitações conhecidas, pendências e o que faria diferente.
- `docs/DEVLOG.md`: registro contínuo do desenvolvimento com IA, tarefa a tarefa.
- `docs/conversas/`: histórico das conversas com a IA (sanitizado).
- `CLAUDE.md`: instruções para o agente de IA neste repositório.
