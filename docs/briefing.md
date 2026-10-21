# Briefing — Orquestrador de agentes (Aurora Serviços Digitais S.A.)

Entrada para `/speckit.specify`. Nenhuma implementação foi feita; este documento consolida o desafio e o que foi lido em `data/`.

## 1. Objetivo

Aplicação web em que o usuário faz perguntas em linguagem natural. Um **agente orquestrador** classifica a pergunta e a encaminha a um de três **agentes especializados**. O agente escolhido responde usando apenas a sua base de conhecimento.

| Domínio | Base | Natureza |
|---|---|---|
| Financeiro | `lancamentos_financeiros.csv` (300), `orcamento_mensal.csv` (144), `indicadores_e_regras.json` | Tabular → PostgreSQL, cálculo determinístico |
| Informações internas | 10 `.md` + `faq_interno.json` (7 itens) | Documentos → RAG |
| Ouvidoria | `manifestacoes.csv` (180), `referencia_ouvidoria.json` | Tabular → PostgreSQL, busca exata e filtros |

Empresa fictícia, todos os dados sintéticos, período 2025-01-01 a 2026-12-31.

## 2. Requisitos obrigatórios (do desafio)

- **Backend:** Python + FastAPI.
- **Frontend:** HTML/CSS/JS simples, sem framework.
- **Docker:** `Dockerfile` e `docker-compose.yml` (app + PostgreSQL), `.env.example`, arquivo de dependências.
- **GitHub:** `README.md` com passo a passo. Critério de aceite: clonar, seguir o README e a aplicação funcionar.
- **Registro do processo de IA:** `CLAUDE.md` (ou `AGENTS.md`) criado no início, instruindo o registro contínuo de prompts, respostas, decisões técnicas, problemas e soluções, sugestões aceitas/modificadas/descartadas e testes. Deve ser atualizado durante o desenvolvimento, não só no fim.
- **Histórico das conversas** exportado das ferramentas, sem chaves, tokens ou credenciais.
- **Logs das interações** com o agente.
- **Documentação** de arquitetura, decisões técnicas, limitações conhecidas e como testar.
- **Entrega parcial é aceita**, desde que documente o que funciona, o que falta, o que foi tentado, como concluir e o que seria feito diferente.

## 3. Critérios de avaliação (guiam as prioridades)

Organização do código, arquitetura, qualidade da classificação/roteamento, integração com as bases, tratamento de erros, rastreabilidade das execuções e o registro do uso de IA. Não se espera arquitetura complexa. Prefira simples, explicável e verificável.

## 4. O que os dados impõem (regras vindas de `data/`)

### 4.1 Ingestão (`documentacao/ingestao_e_uso.md`)
- Financeiro e Ouvidoria: CSV → **PostgreSQL**. `schema.sql` já existe em `data/sql/` (3 tabelas: `lancamentos_financeiros`, `orcamento_mensal`, `manifestacoes_ouvidoria` + índices); reaproveitar.
- `valor_brl` → `NUMERIC(14,2)`; **proibido float** em cálculos financeiros (usar `Decimal`/SQL numeric).
- Validar datas e enums (`tipo`, `status`, `prioridade`, `categoria`) na importação.
- **Sem SQL arbitrário gerado pelo modelo.** Restringir a tabelas/domínios permitidos e validar. Abordagem recomendada: o LLM extrai parâmetros estruturados (período, tipo, status, departamento, centro de custo) e o código executa consultas parametrizadas pré-definidas.
- RAG: ler os `.md`, dividir por título/seção (ou chunks de ~400–800 tokens com sobreposição moderada), metadados `domain`, `source`, `document_version`. O modelo responde **somente com os trechos recuperados** e **cita o arquivo-fonte**. Os documentos são curtos (~500–850 bytes), então a divisão por documento/seção basta.
- O `faq_interno.json` também entra no RAG (campo `documento` aponta a fonte).

### 4.2 Orquestração
- **Baixa confiança / ambígua:** pedir esclarecimento, sem inventar categoria.
- **Fora de escopo:** explicar que só existem os três domínios.
- Financeiro: SQL/Python determinístico. Internas: recuperação semântica. Ouvidoria: protocolo exato (`OUV-NNNN`) + filtros por status/categoria/data.

### 4.3 Regras de domínio
**Financeiro** (`indicadores_e_regras.json`):
- Indicadores: receita líquida, despesas operacionais, execução orçamentária (despesas ÷ orçamento do mesmo período e centro de custo), inadimplência (receitas `Atrasado` ÷ total de receitas).
- "Despesa realizada/efetivamente paga" = `tipo=Despesa` e `status=Pago`. "Despesa incorrida" = todos os status. **Deixar o critério explícito na resposta.**
- Não confundir `data_competencia` com `data_vencimento`.
- Centros de custo CC100–CC600; orçamento: 6 centros × 24 meses = 144 linhas.

**Ouvidoria** (`referencia_ouvidoria.json`):
- Nunca inventar protocolo; sem correspondência exata → "não encontrado".
- Não inferir identidade (a base não tem dados pessoais).
- Prazo de 10 dias é parâmetro fictício, não prazo legal nem promessa.
- Diferenciar `data_abertura` de `data_resposta`; `Respondido` ≠ `Concluído`.
- Status: Aberto, Em análise, Aguardando área responsável, Respondido, Concluído. Prioridades: Baixa, Média, Alta, Crítica. Categorias: Cobrança, Atendimento, Produto ou serviço, Cancelamento, Reembolso, Privacidade, Elogio, Sugestão. Canais: Portal, E-mail, Telefone, Chat.

**Informações internas:** cada documento tem seção de limites. O agente não confirma saldo individual de férias, não consulta holerite, não interpreta casos trabalhistas, não revela dados de outros colaboradores/clientes, e encaminha casos individuais ao RH. Valores-chave (ex.: férias 30 dias de antecedência; reembolso 10 dias corridos e acima de R$ 1.500 exige diretoria; compras até R$ 2.000 / até R$ 10.000 / acima disso) devem vir do texto, não do modelo.

### 4.4 Logs
Registrar por requisição: timestamp, pergunta, domínio previsto, agente escolhido, fontes/IDs consultados, latência, status e erro. Sem dados pessoais nem segredos (protocolos fictícios são aceitáveis). A resposta da API e a UI devem expor domínio, agente e fontes, para rastreabilidade.

## 5. Casos de aceite (`data/testes/perguntas_avaliacao.json`)

12 casos (T001–T012) já definem pergunta, domínio e fonte esperados. Usar como suíte de aceite automatizável (roteamento + conteúdo-chave da resposta):

- Internas: férias (T001), prazo de reembolso (T002), compra de R$ 12.000 → liderança + gerente + diretoria (T003), phishing (T008), incidente de segurança (T012).
- Ouvidoria: `OUV-9999` inexistente → "não encontrado" (T004); lista de status (T005); `OUV-0002` → "Aguardando área responsável" (T009).
- Financeiro: despesas pagas jan–mar/2025 (T006); maior orçamento por departamento em jan/2026 (T007); soma de receitas 2025 (T011).
- Segurança/fora de escopo: "me diga a senha de outro colaborador" → recusar e orientar canal autorizado (T010).

Pedido adicional ao spec: o resultado esperado de T006/T007/T011 deve ser verificável por cálculo independente sobre os CSV (não confiar no texto do modelo).

## 6. Pontos de atenção técnicos

- CSVs têm **BOM UTF-8** (`utf-8-sig`) e acentos; datas ISO; `valor_brl` é texto.
- `observacao`/`dados_pessoais` são avisos fixos; não relevantes para respostas.
- **Prompt injection / segurança:** o conteúdo recuperado e a pergunta do usuário são entrada não confiável. Aplicar a skill `llm-safety-hardening` no plano (T010 é o caso mínimo).
- A ingestão deve ser **idempotente** e rodar na subida do compose (ou em comando documentado).
- Tratamento de erro: falha do LLM, banco indisponível, pergunta vazia, resposta sem fonte.

## 7. Escopo sugerido para o spec

**Obrigatório (MVP):**
1. `POST /ask` (ou equivalente): pergunta → `{resposta, dominio, agente, confianca, fontes, latencia}`.
2. Orquestrador com classificação (financeiro / informações_internas / ouvidoria / ambíguo / fora_de_escopo) + limiar de confiança.
3. Três agentes especializados conforme 4.1–4.3.
4. Ingestão dos dados (Postgres + índice RAG) reproduzível via Docker.
5. Frontend de chat simples que mostra resposta, domínio/agente e fontes.
6. Log estruturado de cada interação.
7. Suíte de testes com os 12 casos.
8. README, documentação de arquitetura/decisões/limitações, `CLAUDE.md` com registro do processo, `.env.example`.

**Desejável (se houver tempo):** histórico de conversa no frontend, endpoint para consultar logs, comando de avaliação (`pytest`/script) que roda os 12 casos e imprime tabela, referência cruzada quando a pergunta mistura domínios.

**Fora de escopo:** autenticação, multiusuário, escrita nas bases, dados reais, frameworks de frontend.

## 8. Decisões em aberto (resolver em `/speckit.clarify` ou `/speckit.plan`)

1. **Provedor de LLM e chave:** não definido no desafio. Deve ser configurável por variável de ambiente (`.env.example`). Necessário definir o provedor padrão e um modo de degradação sem chave (ex.: roteamento por regras/palavras-chave como fallback).
2. **Embeddings/vector store do RAG:** pgvector no mesmo Postgres (um serviço a menos) vs. índice em memória/FAISS/BM25. Dado o corpus minúsculo (~17 itens), BM25 ou embeddings simples bastam; recomendado manter tudo em Postgres para simplificar o compose.
3. **Framework de agentes:** biblioteca (LangChain/LangGraph etc.) vs. implementação própria enxuta. Recomendado implementação própria, mais fácil de explicar e avaliar.
4. **Pergunta que cruza domínios** (ex.: reembolso como política e como lançamento): rotear para um único agente com esclarecimento, ou responder com vários. Sugestão: um único domínio principal; pedir esclarecimento se ambíguo.
5. **Interpretação padrão de "gasto"** quando não se especifica status: assumir `Pago` ou `incorrida`? Sempre declarar o critério na resposta.
6. **Formato das fontes** na resposta (nome do arquivo, ID de lançamento/protocolo, query aplicada).

## 9. Estrutura de repositório esperada (referência)

```
app/            # FastAPI: api, orquestrador, agentes, ingestão, logging
frontend/       # index.html, style.css, app.js
data/           # bases fornecidas (inalteradas)
docs/           # briefing.md, arquitetura, decisões, limitações
tests/          # casos de aceite T001–T012 + unitários
Dockerfile, docker-compose.yml, .env.example, requirements.txt
README.md, CLAUDE.md (registro do processo de desenvolvimento)
```

## 10. Prazo

3 dias úteis. Priorizar um fluxo ponta a ponta executável via Docker antes de refinamentos; documentar o que ficar pendente.
