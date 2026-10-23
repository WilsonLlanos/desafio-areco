# Limitações conhecidas e pendências

## Limitações

**Segurança (detecção por padrões)**
- As guardas pré-LLM (credenciais, dados de terceiros, prompt injection) são expressões regulares em
  português (e inglês, no caso de injeção). Paráfrase, outro idioma ou ofuscação passam por elas. No
  smoke test, um pedido de senha em espanhol foi barrado pelo modelo, não pela guarda. As defesas que
  não dependem do modelo são as estruturais: consultas fixas, papel `ro`, contratos de saída e fontes
  escritas por código.
- Falso positivo conhecido: "Posso enviar dados de clientes a ferramentas externas?" é recusada.
- O smoke test adversarial foi informal (8 prompts, uma execução cada): mostra que os ataques óbvios
  não funcionaram com este modelo, não que o sistema é seguro.
- Uma linha com padrão de injeção tira o documento inteiro do índice (o item é o documento).

**Logs e dados pessoais**
- A pergunta é gravada como digitada (exigência de rastreabilidade da constituição I). Se o usuário
  digitar um dado pessoal, ele vai para `logs/interactions.jsonl`. Os dados da base são sintéticos.
- A API não tem autenticação nem limite de requisições: é uma demonstração interna.

**Recuperação e respostas**
- Radical por truncamento (6 letras) e `ESCORE_MINIMO` calibrados com os 12 casos de avaliação; perguntas
  muito diferentes podem cair em "não encontrei" ou no documento errado.
- Sem LLM, a resposta de informações internas é extrativa (linhas do documento) e pode trazer linhas
  pouco relevantes em perguntas genéricas.
- Cada pergunta é independente: não há memória de conversa ("e em fevereiro?" não funciona).

**Provedor de LLM**
- Uma tentativa por chamada, timeout de 10 s (mínimo da API). No plano gratuito o provedor devolveu
  muitos 503/504: as respostas saem corretas pelas regras, mas marcadas `degradado`. Uma chamada lenta
  seguida de um timeout pode passar de 10 s. No nível 1 (pago), o p90 medido foi 2,5 s.
- Classificação e parâmetros dependem do modelo; o contrato impede valores inválidos, mas não um
  parâmetro válido e errado. Exemplo visto: antes dos exemplos no prompt, o modelo leu "abertas em
  janeiro" como status Aberto (corrigido e reverificado na Fase 5).

**Avaliação**
- 12 casos são poucos para medir qualidade; a suíte cobre os cenários do briefing, não variações.
- O juiz (`gemini-3.5-flash`) é da mesma família do modelo avaliado e não é o Pro planejado (404/429 na
  chave): risco de viés favorável. Mitigação: referência explícita por caso, rubrica fixa, temperatura 0
  e decisão final determinística (o juiz nunca reprova nem aprova sozinho).

## Pendências

| Item | Estado | Como concluir |
|---|---|---|
| Juiz Gemini Pro (decisão original) | não usado: `gemini-2.5-pro` 404 para contas novas; `gemini-3.1-pro-preview` 429 no plano gratuito | com a chave no nível 1, definir `JUDGE_MODEL=gemini-3.1-pro-preview` e rodar `scripts/evaluate.py` |
| Juiz de outra família | não implementado | `scripts/judge.py` recebe o gerador injetado; basta outro `gerar` (ex.: Claude) |
| Guardas multilíngues / classificador dedicado | não implementado | classificador de injeção (ex.: Prompt Guard) antes do LLM; conjunto adversarial maior e versionado |
| Limite de tempo total por requisição | não implementado | orçamento de tempo no estado do grafo (pular o LLM se o tempo restante for menor que o timeout) |

## O que faria diferente

- Escrever as notas do DEVLOG tarefa a tarefa desde a Fase 1 (nas Fases 1 e 2 foram escritas em lote;
  corrigido a partir da Fase 3).
- Testar o provedor com a chave real logo no início: o limite do plano gratuito, o timeout mínimo de
  10 s e a recusa do `response_schema` só apareceram na Fase 4.
- Separar desde o plano "resposta correta" de "resposta com LLM" na avaliação (o achado U5 veio da análise
  pós-Fase 4, antes da primeira execução real, e evitou um relatório enganoso).
