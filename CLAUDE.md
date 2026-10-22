# CLAUDE.md — Desafio Aurora (Orquestrador de Agentes)

Instruções para o agente de IA que trabalha neste repositório. A fonte de verdade dos princípios é
`.specify/memory/constitution.md` (v1.2.1); este arquivo resume o que importa no dia a dia.

## Contexto

Aplicação web (FastAPI + frontend HTML/CSS/JS simples + PostgreSQL + Docker) em que um orquestrador
(LangGraph) classifica perguntas e as encaminha a três agentes: financeiro, informações internas e
ouvidoria. Briefing: `docs/briefing.md`. Spec, plano e tarefas: `specs/001-orquestrador-agentes/`.
O desafio avalia **como o desenvolvimento é conduzido com IA**, não só o resultado final.

## Registro contínuo no DEVLOG (constitution, princípio VI)

`docs/DEVLOG.md` é atualizado **durante** o desenvolvimento, nunca só no fim.

1. **A cada tarefa concluída** (`tasks.md`), acrescentar ao DEVLOG uma nota curta (poucas linhas):
   - o que foi feito (ID da tarefa);
   - decisão ou problema relevante;
   - sugestão de IA **aceita / modificada / descartada**, quando houver;
   - teste executado e resultado.
2. **Ao final de cada fase**, acrescentar o **resumo da fase**: objetivo, o que funciona, decisões
   técnicas, problemas e soluções, testes e validações, limitações e pendências.
3. Tarefa sem nota ou fase sem resumo **não é considerada concluída**. Marcar `[X]` no `tasks.md`
   só depois da nota.
4. Registrar o que realmente aconteceu, inclusive erros e sugestões descartadas. Não embelezar.
5. Registro feito depois do fato deve ser marcado como **registrado retroativamente**, com a
   fonte usada para reconstruí-lo.
6. Sem segredos, tokens ou dados pessoais no DEVLOG (princípio VII).

## Histórico das conversas

As sessões do Claude Code ficam em `~/.claude/projects/-home-wilso-projetos-desafio-areco/`
(JSONL). As exportações entregáveis vão para `docs/conversas/`, descritas no README dessa pasta
(origem de cada arquivo). Sanitizar antes de versionar: chaves de API, tokens, credenciais e
dados pessoais (inclusive e-mail do usuário). A exportação é feita uma vez, no fim do projeto
(T065), porque uma mesma sessão atravessa várias fases; até lá, as transcrições JSONL locais são a
fonte e não devem ser apagadas.

## Regras de trabalho

- **Fases (princípio IX)**: ao terminar uma fase, parar e aguardar aprovação explícita do usuário.
  Um commit por fase. Gate: `docker compose up` funcional, `pytest` verde, DEVLOG atualizado,
  nenhum segredo no diff.
- **Sem SQL do modelo (II)**: o LLM só extrai parâmetros validados; consultas são pré-definidas,
  parametrizadas, com papel de banco somente leitura. Valores monetários em `Decimal`/`NUMERIC`.
- **Rastreabilidade (I)**: `trace_id` em toda requisição, log JSON por requisição, sem dados sensíveis.
- **Respostas com fonte (VIII)**: números e fontes escritos por código; protocolo inexistente →
  "não encontrado"; conteúdo recuperado e entrada do usuário são não confiáveis.
- **Testes (V)**: `pytest` com LLM fake e sem rede; avaliação AV-T001–AV-T012 em script separado,
  com LLM real. Casos de avaliação são `AV-Txxx`; tarefas são `Txxx`.
- **Simplicidade (IV)**: LangGraph só para o grafo de orquestração; sem tool-calling livre.
- `data/` não é alterado. CSVs lidos com `utf-8-sig`. Commits só quando o usuário pedir.
- Respostas e documentação em português do Brasil.
