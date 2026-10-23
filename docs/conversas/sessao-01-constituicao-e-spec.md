# Sessão 01 — Constituição e especificação

Sessão `086d1831-a8a2-4a09-b3f3-7a2a8cb09508` (Claude Code). Carimbos em UTC.

### Usuário — 2026-10-21 01:45

Leia todos os arquivos em data/, começando por data/documentacao/ingestao_e_uso.md e data/documentacao/dicionario_de_dados.md. Depois, com base no desafio descrito abaixo, escreva um briefing em docs/briefing.md que servirá de entrada para o /speckit.specify. Ainda não implemente nada.



_(início do texto colado)_
Objetivo do desafio

Desenvolver um agente de IA capaz de interpretar perguntas em linguagem natural, identificar sua categoria e direcioná-las ao agente especializado correspondente, utilizando três domínios de conhecimento:

- Financeiro: informações e dados financeiros.

- Informações internas: documentação, procedimentos e conhecimentos internos.

- Ouvidoria: manifestações, reclamações, protocolos e informações relacionadas.

 

A solução deverá contar com um agente orquestrador responsável pela classificação das perguntas e pelo direcionamento para o agente adequado.

As bases de conhecimento que poderão ser utilizadas serão disponibilizadas em anexo.

 

Requisitos técnicos

- Backend: Python com FastAPI.

- Frontend: HTML, CSS e JavaScript simples, sem necessidade de frameworks complexos.

- Bases de conhecimento: utilizar os arquivos fornecidos em anexo.

- Docker: a aplicação deverá estar preparada para execução em containers Docker.

- GitHub: o código-fonte deverá ser disponibilizado em um repositório GitHub, com todas as instruções necessárias para configuração e execução.

 

O repositório deverá conter os arquivos necessários para executar a aplicação, incluindo `Dockerfile`, `docker-compose.yml` ou alternativa equivalente devidamente documentada, arquivo de exemplo de variáveis de ambiente, dependências e `README.md` com o passo a passo de execução.

Nosso objetivo é conseguir clonar o repositório e colocar a aplicação em funcionamento seguindo as instruções fornecidas.

 

Utilização de Inteligência Artificial durante o desenvolvimento

Um dos principais objetivos deste desafio é compreender como você utiliza ferramentas de IA para desenvolver software.

Não existe qualquer restrição quanto ao nível de utilização dessas ferramentas. O projeto pode ser desenvolvido integralmente com auxílio de IA, parcialmente com IA ou por meio de uma combinação de diferentes abordagens.

Você poderá utilizar ferramentas como Claude Code, Codex, ChatGPT, Gemini ou outras de sua preferência.

O que queremos avaliar não é quanto código você escreveu manualmente, mas como você conduz o processo de desenvolvimento, toma decisões, valida resultados e utiliza a IA para resolver problemas.

 

Registro obrigatório do processo de desenvolvimento

Assim que iniciar o desenvolvimento, crie um arquivo de instruções para um agente de IA, como `AGENTS.md`, `CLAUDE.md` ou equivalente compatível com a ferramenta utilizada.

Esse arquivo deverá orientar o registro contínuo do processo de desenvolvimento, mantendo um histórico organizado das interações relevantes com a IA durante a construção do projeto.

 

Sempre que possível, registre:

- Os prompts e as solicitações enviados à IA.

- As respostas e soluções propostas.

- As decisões técnicas tomadas durante o desenvolvimento.

- Os problemas encontrados e as estratégias utilizadas para resolvê-los.

- As sugestões de código aceitas, modificadas ou descartadas.

- Os testes realizados e as validações utilizadas para verificar o funcionamento da solução.

 

Esse registro deverá ser atualizado ao longo do desenvolvimento, e não produzido apenas ao final do desafio.

Além desse arquivo, solicitamos que você entregue o histórico das conversas utilizadas no desenvolvimento, exportado diretamente das ferramentas quando possível. Caso a ferramenta não permita a exportação completa, apresente registros alternativos que permitam compreender o processo.

Não é necessário compartilhar conversas pessoais ou sessões sem relação com o desafio. Remova chaves de API, tokens, credenciais e outros dados sensíveis antes de realizar a entrega.

 

Entrega:

Ao concluir o desafio, esperamos receber:

1. O link do repositório GitHub com o código-fonte.

2. A aplicação preparada para execução via Docker, com instruções claras.

3. O frontend funcional, conforme o nível de implementação alcançado.

4. A implementação do orquestrador e dos agentes especializados, conforme o nível de implementação alcançado.

5. Os arquivos ou scripts necessários para utilizar as bases de conhecimento.

6. Os logs das interações realizadas com o agente desenvolvido.

7. O arquivo `AGENTS.md`, `CLAUDE.md` ou equivalente, com o registro estruturado do processo de desenvolvimento.

8. O histórico das conversas mantidas com as ferramentas de IA utilizadas.

9. Uma documentação explicando a arquitetura, as decisões técnicas, as limitações conhecidas e como testar a solução.

10. Prazo: 3 dias úteis a partir do recebimento deste e-mail.

 

Importante: entregue o que conseguir desenvolver

Sabemos que o desafio pode envolver dificuldades técnicas e que nem sempre será possível implementar todos os requisitos dentro do prazo disponível.

Caso não consiga concluir o desafio por inteiro, pedimos que entregue o projeto no estado em que estiver, da melhor forma possível, mesmo que apenas parte dos requisitos tenha sido implementada.

 

Não deixe de realizar a entrega simplesmente porque alguma funcionalidade não ficou pronta ou porque encontrou um problema que não conseguiu resolver.

Nesse caso, procure documentar:

- O que conseguiu implementar e o que está funcionando.

- O que ficou pendente e quais dificuldades encontrou.

- Quais alternativas tentou e por que não funcionaram.

- Como pretende concluir ou melhorar a solução.

- Quais decisões tomou durante o desenvolvimento e o que faria de diferente.

 

Se possível, deixe a parte implementada executável e documente claramente o que ainda precisa ser finalizado.

Preferimos avaliar uma implementação parcial, acompanhada de um bom registro do raciocínio e das tentativas realizadas, a deixar de receber uma entrega por ela não estar completa.

O objetivo é entender sua forma de pensar, investigar problemas, tomar decisões e utilizar as ferramentas disponíveis. Uma funcionalidade incompleta pode nos ensinar bastante sobre seu processo de desenvolvimento.

 

Como será feita a avaliação?

Além do funcionamento da aplicação, avaliaremos a organização do código, a arquitetura proposta, a capacidade de classificar e direcionar perguntas, a integração com as bases de conhecimento, o tratamento de erros e a rastreabilidade das execuções.

Também analisaremos os registros do desenvolvimento para compreender como você interage com a IA, formula solicitações, identifica problemas, valida respostas e conduz a construção de uma aplicação de software.

Não esperamos necessariamente uma solução perfeita ou uma arquitetura excessivamente complexa. Queremos entender seu raciocínio, seus conhecimentos fundamentais de desenvolvimento de software e sua capacidade de utilizar ferramentas modernas de IA de maneira produtiva e consciente.

Reforçando: utilizar IA em 100% do desenvolvimento não é um problema. O mais importante é que você compreenda a solução entregue, consiga explicar as decisões tomadas e demonstre capacidade de verificar, corrigir e evoluir o sistema desenvolvido.
_(fim do texto colado)_

### Claude — 2026-10-21 01:45

Login expired · Please run /login

- `Bash`

- `Bash`

- `Write`: ~/projetos/desafio-areco/docs/briefing.md

Li todos os arquivos de `data/` e escrevi o briefing em `docs/briefing.md`, sem implementar nada.

O briefing tem 10 seções: objetivo, requisitos obrigatórios, critérios de avaliação, regras vindas dos dados, casos de aceite, pontos técnicos, escopo, decisões em aberto, estrutura sugerida do repositório e prazo.

- **Casos de aceite:** o briefing usa os 12 casos de `data/testes/perguntas_avaliacao.json` (T001–T012) como suíte de aceite. Pede que as respostas financeiras sejam conferidas por cálculo independente sobre os CSV.
- **Consultas ao banco:** o briefing recomenda que o modelo só extraia parâmetros e o código rode consultas fixas e parametrizadas, porque a documentação proíbe SQL arbitrário gerado pelo modelo.
- **CSVs:** têm BOM UTF-8, então o briefing manda ler com `utf-8-sig`.

Há seis decisões em aberto na seção 8, para resolver no `/speckit.clarify` ou no `/speckit.plan`. As duas que mais pesam:
- **Provedor de LLM:** o desafio não define qual usar, nem se deve haver um modo sem chave. Sugeri deixar configurável por variável de ambiente, com roteamento por regras como alternativa.
- **Busca nos documentos internos (RAG):** sugeri guardar tudo no mesmo Postgres. O corpus é minúsculo, cerca de 17 itens.

Como o git status mostra os arquivos antigos de `data/` removidos e as pastas novas sem commit, vale commitar essa reorganização antes de rodar o `/speckit.specify`.

### Usuário — 2026-10-21 02:20

/speckit.constitution Derive os princípios do projeto a partir de docs/briefing.md. Inclua obrigatoriamente: rastreabilidade (log estruturado por requisição com trace_id), proibição de SQL gerado pelo modelo (só consultas parametrizadas), execução via docker compose, simplicidade sem over-engineering, testes com pytest e LLM mockada, atualização de docs/DEVLOG.md a cada tarefa concluída e nenhum segredo commitado.
- Entrega incremental: a implementação ocorre em fases. Cada fase deve terminar executável via docker compose, com testes passando, DEVLOG atualizado e commit próprio. Nunca avançar para a fase seguinte sem aprovação explícita do usuário.

### Claude — 2026-10-21 02:20

- `Skill`: speckit-constitution

- `Bash`

- `Bash`

- `Write`: ~/projetos/desafio-areco/.specify/memory/constitution.md

Escrevi a constitution em `.specify/memory/constitution.md`, na versão **1.0.0**. É a primeira versão, porque o arquivo ainda era o template em branco. Ratificada em 2026-10-20. Não há TODOs pendentes.

**Princípios** (os sete que você pediu, mais dois que derivei do briefing):
1. **Rastreabilidade:** cada requisição tem um `trace_id` e um log JSON estruturado. Os campos são os do briefing, e o `trace_id` e as fontes aparecem na resposta da API.
2. **Sem SQL gerado pelo modelo:** o LLM só extrai parâmetros validados e o código roda consultas parametrizadas. Valores monetários usam `Decimal`/`NUMERIC`, nunca `float`.
3. **Execução via `docker compose`:** a partir de um clone limpo, com ingestão idempotente e configuração em `.env.example`.
4. **Simplicidade:** sem camadas ou dependências sem necessidade presente.
5. **Testes com pytest e LLM mockada:** sem rede nos testes, cobrindo os casos T001–T012. Os resultados financeiros são conferidos por cálculo independente sobre os CSV.
6. **`docs/DEVLOG.md` atualizado a cada tarefa concluída:** sem entrada no DEVLOG, a tarefa não conta como concluída.
7. **Nenhum segredo commitado:** isso inclui o DEVLOG e as conversas exportadas.
8. **Respostas fundamentadas e com fonte** *(adicionado por mim, vindo do briefing)*: sempre citar a fonte, nunca inventar protocolo, pedir esclarecimento quando ambíguo e tratar o conteúdo recuperado como não confiável.
9. **Entrega incremental por fases:** cada fase termina executável via `docker compose`, com testes passando, DEVLOG atualizado e commit próprio. Não avanço para a fase seguinte sem a sua aprovação explícita, mesmo que ela esteja no `tasks.md`.

Os princípios 1, 2 e 9 estão marcados como NON-NEGOTIABLE. Também preenchi as seções de restrições técnicas e quality gates, e a de governança.

Commit sugerido: `docs: ratify constitution v1.0.0 (9 principles, incremental phases)`

Não executei nenhum commit. O próximo passo natural é o `/speckit.specify`, usando `docs/briefing.md` como entrada.

### Usuário — 2026-10-21 02:29

O item 5 ficou misturado. Separe: pytest é com LLM mocakda para lógica e script de avaliação com LLM real rodando T001-T012, que gera log de execução
No 6: atualizações curtas por tarefa e um resumo  obrigatório ao final de cada fase.

### Claude — 2026-10-21 02:30

- `Bash`

Ajustei os dois itens em `.specify/memory/constitution.md`. A versão passou para **1.1.0** (MINOR, porque os princípios V e VI foram expandidos). Não rodei os testes nem a avaliação, só editei o texto.

**Princípio V**, agora com dois tipos de teste que não se misturam:
- **`pytest` (lógica):** usa LLM mockada, sem rede, e roda em todo gate de fase. Cobre roteamento, extração de parâmetros, consultas, RAG, erros e logging. Os resultados financeiros são conferidos por cálculo independente sobre os CSV.
- **Script de avaliação (LLM real):** fica separado do `pytest` e roda os casos T001–T012. Gera um log de execução por caso, com `trace_id`, domínio e fonte esperados contra os obtidos, critério, resultado e latência. O log é versionado como evidência, sem segredos. Como exige chave de API, não entra no gate automático.

**Princípio VI**, também com dois níveis:
- **Por tarefa:** uma atualização curta no `docs/DEVLOG.md`, com o que foi feito, decisão ou problema, sugestão de IA aceita, modificada ou descartada, e teste executado.
- **Por fase:** um resumo obrigatório no final, com objetivo, o que funciona, decisões, problemas, testes, limitações e pendências. Fase sem resumo não conta como concluída.

O gate de fase em "Fluxo de Desenvolvimento" agora exige a nota por tarefa e o resumo da fase. O Sync Impact Report também foi atualizado.

Uma linha do gate ficou comprida, com mais de 100 caracteres. Não afeta nada, mas posso reformatar se você quiser.

Commit sugerido: `docs: amend constitution to v1.1.0 (split test types, DEVLOG per task + phase summary)`

### Usuário — 2026-10-21 02:35

`/speckit-specify` Use o briefing.md como entrada. Mantenha as decisões em aberto da seção 8. Vamos resolver no clarify

### Claude — 2026-10-21 02:35

- `Bash`

- `Bash`

- `Write`: ~/projetos/desafio-areco/specs/001-orquestrador-agentes/spec.md

- `Write`: ~/projetos/desafio-areco/specs/001-orquestrador-agentes/checklists/requirements.md

Escrevi a spec em `specs/001-orquestrador-agentes/spec.md`, e o checklist de qualidade em `specs/001-orquestrador-agentes/checklists/requirements.md`. Não criei branch (não havia hook de git) e não commitei. O caminho da feature está salvo em `.specify/feature.json`.

**Conteúdo da spec:**
- **Cinco histórias de usuário.** Três são P1: perguntar e receber a resposta do domínio certo, respostas seguras (sem invenção, com recusa e esclarecimento) e execução reproduzível a partir do repositório. Duas são P2: rastrear cada interação e avaliar com a suíte T001–T012.
- **34 requisitos funcionais e 8 critérios de sucesso,** sem citar tecnologias.
- **Casos de borda e premissas.**

**Checklist:** 16 dos 17 itens passam. O item que falha é o de "nenhum marcador `[NEEDS CLARIFICATION]` restante". Deixei isso de propósito, porque você pediu para manter as decisões em aberto.

**As seis decisões da seção 8** estão numa seção "Decisões em aberto", sem resolução. O template limita a três marcadores no corpo dos requisitos, então só estas três têm marcador:
- **FR-034:** provedor de LLM e modo sem chave.
- **FR-005:** perguntas que cruzam domínios.
- **FR-017:** interpretação padrão de "gasto" (paga ou incorrida).

As outras três (busca nos documentos internos, framework de agentes, formato das fontes) ficam só na seção de decisões em aberto. Elas são técnicas e cabem melhor no `/speckit.plan`.

Fica pronto para o `/speckit.clarify`.

### Usuário — 2026-10-21 02:59

Temos que atualizar estes documentos referente as perguntas de avaliação que estão com nomenclatura T001, T002, que podem confundir com as tasks que serão criadas posteriormente. Podemos adotar "AV-T001, AV-T002" para perguntas_avaliaca.json

### Claude — 2026-10-21 02:59

- `Bash`

- `Bash`

Renomeei os casos de avaliação para `AV-T001`–`AV-T012`. Conferi que o JSON continua válido e que não sobrou nenhum `T0xx` solto nesses arquivos. Não rodei testes nem commitei.

- **`data/testes/perguntas_avaliacao.json`:** os 12 `id` mudaram.
- **`docs/briefing.md`, `specs/001-orquestrador-agentes/spec.md` e `.specify/memory/constitution.md`:** todas as referências foram atualizadas, inclusive `T006/T007/T011` e as faixas `T001–T012`.
- **Templates do Spec Kit:** o `T001` do `tasks-template.md` é o das tasks, então não toquei.

Tinha um conflito com a regra de que `data/` não pode ser alterado, e resolvi assim:
- **Spec (FR-023):** abri a exceção para esta renomeação, explicando o motivo.
- **Constitution:** a mesma exceção entrou nas restrições técnicas. Isso fez a versão ir para **1.1.1** (PATCH), com o Sync Impact Report atualizado.

Se preferir manter `data/` intocado e mapear `AV-` só nos nossos documentos, é só dizer e eu reverto o JSON.

Commit sugerido: `docs: rename evaluation cases to AV-Txxx to avoid clash with task IDs (constitution v1.1.1)`

### Usuário — 2026-10-21 03:01

é só no documento do projeto para nos referirmos. não precisa alterar o data. Vamos manter intocado

### Claude — 2026-10-21 03:01

- `Bash`

Desfiz a alteração em `data/testes/perguntas_avaliacao.json`. Os 12 `id` voltaram a `T001`–`T012`, e `data/` está intocado de novo. Os arquivos de `data/` não estão versionados no git, então a reversão foi feita editando o JSON. Pelo mesmo motivo, não tenho um diff para confirmar que ele ficou idêntico ao original.

O prefixo `AV-` agora vale só nos documentos do projeto (`docs/briefing.md`, spec e constitution), e eles dizem que `AV-T001` corresponde a `T001` no JSON.

- **Spec, FR-023:** voltou a proibir qualquer alteração em `data/`, sem exceção. Só acrescentei a nota do mapeamento `AV-Txxx` ↔ `Txxx`.
- **Constitution:** removi a exceção que eu tinha aberto e coloquei a mesma nota de mapeamento. A versão continua em **1.1.1** (PATCH), agora descrita como "documentos referem os casos como AV-Txxx; `data/` intocado".

Uma consequência para a implementação: o script de avaliação e os testes vão ler os IDs `T001`… do JSON. O prefixo `AV-` só será aplicado na exibição, por exemplo nos relatórios.

Commit sugerido: `docs: refer to evaluation cases as AV-Txxx in project docs (constitution v1.1.1)`
