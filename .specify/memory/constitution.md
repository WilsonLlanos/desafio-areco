<!--
Sync Impact Report
- Version change: 1.2.0 → 1.2.1 (PATCH: princípio V esclarece "sem rede" = sem rede externa nem LLM real; PostgreSQL local/do compose é permitido)
- Histórico: 1.1.1 → 1.2.0 (MINOR: princípio IV passa a permitir LangGraph como orquestrador de agentes); 1.1.0 → 1.1.1 (PATCH: documentos referem os casos de avaliação como AV-Txxx; data/ intocado); 1.0.0 → 1.1.0 (MINOR: princípios V e VI expandidos)
  (1.0.0 foi a versão inicial, a partir do template não preenchido)
- Princípios adicionados: I. Rastreabilidade; II. Consultas parametrizadas, nunca SQL do modelo;
  III. Docker Compose como único meio de execução; IV. Simplicidade; V. Testes (pytest com LLM mockada + script de avaliação com LLM real);
  VI. Registro contínuo em docs/DEVLOG.md (nota curta por tarefa + resumo por fase); VII. Nenhum segredo commitado;
  VIII. Respostas fundamentadas e com fonte; IX. Entrega incremental por fases
- Seções adicionadas: Restrições Técnicas e de Escopo; Fluxo de Desenvolvimento e Quality Gates; Governance
- Seções removidas: nenhuma
- TODOs adiados: nenhum
-->
# Desafio Aurora — Orquestrador de Agentes Constitution

## Core Principles

### I. Rastreabilidade (NON-NEGOTIABLE)
Toda requisição ao agente MUST receber um `trace_id` único, gerado na entrada da API e propagado
por orquestrador, agentes, consultas e resposta. Cada requisição MUST gerar um log estruturado (JSON)
com: timestamp, `trace_id`, pergunta, domínio previsto, confiança, agente escolhido, fontes/IDs
consultados, latência, status e erro. Logs MUST NOT conter dados pessoais ou segredos. A resposta da
API MUST expor `trace_id`, domínio, agente e fontes.
Racional: rastreabilidade das execuções é critério explícito de avaliação do desafio.

### II. Consultas parametrizadas, nunca SQL gerado pelo modelo (NON-NEGOTIABLE)
O LLM MUST NOT produzir SQL executado pelo sistema. Ele só pode extrair parâmetros estruturados
(período, tipo, status, departamento, centro de custo, protocolo), validados contra enums e formatos
permitidos. O acesso a dados MUST usar consultas pré-definidas e parametrizadas, restritas às tabelas
dos domínios financeiro e ouvidoria. Valores monetários MUST usar `NUMERIC`/`Decimal`, nunca `float`.
Cálculos financeiros MUST ser determinísticos e declarar o critério usado (ex.: despesa paga vs.
incorrida; competência vs. vencimento).

### III. Execução via Docker Compose
A aplicação (API, frontend, PostgreSQL e ingestão) MUST subir com `docker compose up` a partir de um
clone limpo, seguindo apenas o `README.md`. A ingestão dos dados MUST ser idempotente. Configuração
MUST vir de variáveis de ambiente documentadas em `.env.example`.

### IV. Simplicidade, sem over-engineering
Implementar apenas o necessário para o escopo do briefing. Frameworks de agentes são
permitidos; adota-se LangGraph apenas para o grafo de orquestração (sem LangChain além do necessário);
frontend em HTML/CSS/JS puro. Novas camadas, dependências ou abstrações MUST
ser justificadas por uma necessidade presente (YAGNI); a justificativa MUST ficar no plano ou no
DEVLOG. O código MUST ser explicável pelo autor.

### V. Testes: pytest com LLM mockada e avaliação com LLM real
Os testes são de duas naturezas distintas e MUST NOT ser misturados:
- **Testes `pytest` (lógica):** MUST usar LLM mockada/fake (cliente injetável) e MUST NOT acessar
  rede externa nem LLM real (o PostgreSQL local ou do Docker Compose é permitido). Cobrem roteamento, extração de parâmetros, consultas parametrizadas, RAG, tratamento
  de erros e logging. Resultados financeiros MUST ser conferidos por cálculo independente sobre os CSV.
  Rodam em todo gate de fase.
- **Script de avaliação (LLM real):** um script separado, fora do `pytest`, MUST executar os casos
  AV-T001–AV-T012 de `data/testes/perguntas_avaliacao.json` contra o sistema com LLM real e gerar um log de
  execução (por caso: `trace_id`, domínio esperado vs. obtido, fonte esperada vs. obtida, critério,
  resultado, latência). O log MUST ser versionado como evidência, sem segredos. Requer chave de API e
  por isso não roda no gate automático.

### VI. Registro contínuo em docs/DEVLOG.md
A cada tarefa concluída, `docs/DEVLOG.md` MUST receber uma atualização curta (poucas linhas):
o que foi feito, decisão ou problema relevante, sugestão de IA aceita/modificada/descartada e teste
executado. Ao final de cada fase, MUST ser adicionado um resumo obrigatório da fase: objetivo, o que
funciona, decisões técnicas, problemas e soluções, testes e validações, limitações e pendências. O
registro MUST ocorrer durante o desenvolvimento, não ao final. Uma tarefa sem atualização, ou uma fase
sem resumo, não é considerada concluída.

### VII. Nenhum segredo commitado
Chaves de API, tokens e credenciais MUST NOT ser commitados, nem no código, nos logs, no DEVLOG ou em
históricos de conversa exportados. Apenas `.env.example` (sem valores reais) vai ao repositório;
`.env` MUST estar no `.gitignore`. Exportações de conversas MUST ser revisadas e sanitizadas antes da
entrega.

### VIII. Respostas fundamentadas e com fonte
Agentes MUST responder apenas com base em suas bases de conhecimento e MUST citar a fonte (arquivo,
ID de lançamento ou protocolo). Protocolos MUST NOT ser inventados: sem correspondência exata,
informar "não encontrado". Pergunta ambígua ou de baixa confiança MUST gerar pedido de esclarecimento;
pergunta fora dos três domínios MUST receber explicação de escopo. Conteúdo recuperado e entrada do
usuário são não confiáveis (prompt injection); pedidos de credenciais ou dados de terceiros MUST ser
recusados. Falhas (LLM, banco, entrada inválida) MUST ser tratadas com erro claro, sem derrubar a API.

### IX. Entrega incremental por fases (NON-NEGOTIABLE)
A implementação ocorre em fases. Cada fase MUST terminar: executável via `docker compose`, com testes
passando, `docs/DEVLOG.md` atualizado e commit próprio. O agente MUST NOT avançar para a fase seguinte
sem aprovação explícita do usuário, mesmo que a fase seguinte esteja planejada em `tasks.md`.

## Restrições Técnicas e de Escopo

- Backend: Python + FastAPI. Frontend: HTML, CSS e JavaScript simples. Dados tabulares em PostgreSQL
  (reaproveitar `data/sql/schema.sql`); documentos internos via RAG com citação do arquivo-fonte.
- Arquivos em `data/` são as bases fornecidas e MUST NOT ser alterados. Nos documentos do projeto, os casos de
  avaliação são referidos com prefixo `AV-` (`AV-T001`–`AV-T012`, correspondentes a `T001`–`T012` em
  `perguntas_avaliacao.json`), para não colidir com os IDs de tarefas do `tasks.md`; CSVs são lidos com
  `utf-8-sig`.
- Dados são sintéticos; a aplicação MUST NOT sugerir que representem registros reais.
- Fora de escopo: autenticação, multiusuário, escrita nas bases, frameworks de frontend.
- Entregáveis obrigatórios: `README.md`, `Dockerfile`, `docker-compose.yml`, `.env.example`,
  dependências, `CLAUDE.md`/`AGENTS.md`, `docs/DEVLOG.md`, documentação de arquitetura, decisões e
  limitações.

## Fluxo de Desenvolvimento e Quality Gates

- Fluxo Spec Kit: constitution → specify → clarify → plan → tasks → implement, por fase.
- Gate de fase (antes do commit): `docker compose up` funcional, `pytest` verde, DEVLOG atualizado (nota por tarefa + resumo da fase),
  nenhum segredo no diff.
- Um commit por fase, com mensagem descritiva. Entrega parcial é aceitável, desde que limitações e
  pendências estejam documentadas.
- Revisões e planos MUST verificar conformidade com esta constitution; desvios MUST ser justificados
  por escrito.

## Governance

Esta constitution prevalece sobre outras práticas do projeto. Emendas exigem: descrição da mudança,
atualização do Sync Impact Report, incremento de versão e registro no DEVLOG. Versionamento semântico:
MAJOR para remoção ou redefinição incompatível de princípios; MINOR para novo princípio ou expansão
material; PATCH para esclarecimentos. A conformidade é verificada no gate de cada fase e na etapa de
plano (Constitution Check). Orientação de uso diário: `CLAUDE.md` e `docs/DEVLOG.md`.

**Version**: 1.2.1 | **Ratified**: 2026-10-20 | **Last Amended**: 2026-10-21
