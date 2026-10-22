# Feature Specification: Orquestrador de Agentes de Perguntas (Aurora)

**Feature Branch**: `001-orquestrador-agentes` (branch criada a partir de `main`)

**Created**: 2026-10-20

**Status**: Clarified

**Input**: User description: "Use o briefing.md como entrada. Mantenha as decisões em aberto da seção 8. Vamos resolver no clarify" (fonte: `docs/briefing.md`)

## Clarifications

### Session 2026-10-21

- Q: Perguntas multi-domínio? → A: Pedir esclarecimento (FR-005).
- Q: Critério padrão de "gasto"? → A: Despesa incorrida, declarada (FR-017).
- Q: Provedor de LLM e sem chave? → A: Gemini; fallback por regras com aviso (FR-034).
- Q: Pergunta financeira sem período? → A: Pedir o período (FR-035).
- Q: "Receita líquida" sem deduções na base? → A: Total de receitas, declarando que não há deduções registradas (FR-036).
- Q: Tamanho máximo de listas? → A: 10 itens mais o total (FR-010).
- Q: Execução orçamentária sem critério de despesa? → A: Despesas pagas, pois o indicador é "despesas realizadas ÷ orçamento"; declarado na resposta (FR-037; decisão da IA na Fase 2, aprovada após `/speckit-analyze`).
- Q: Inadimplência em valor ou em quantidade? → A: Em valor, declarado na resposta (FR-038; idem).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Perguntar e receber resposta do domínio certo (Priority: P1)

Um colaborador da Aurora abre a página de chat, digita uma pergunta em linguagem natural e recebe uma resposta fundamentada. O sistema identifica sozinho se a pergunta é de **informações internas** (políticas e procedimentos), **ouvidoria** (protocolos e manifestações) ou **financeiro** (lançamentos e orçamento), e encaminha ao agente especializado. A resposta mostra qual domínio e agente atenderam e quais fontes foram usadas.

**Why this priority**: É o núcleo do desafio (classificar e direcionar). Sem isso não há produto.

**Independent Test**: Enviar as 12 perguntas de `data/testes/perguntas_avaliacao.json` e verificar domínio, fonte e conteúdo-chave de cada resposta.

**Acceptance Scenarios**:

1. **Given** o sistema em execução, **When** o usuário pergunta "Como solicito férias?", **Then** a resposta cita o portal interno e 30 dias corridos de antecedência e indica a fonte `01_politica_ferias.md`, com domínio "informações internas".
2. **Given** o sistema em execução, **When** o usuário pergunta "Qual o status do protocolo OUV-0002?", **Then** a resposta informa "Aguardando área responsável" com fonte na base de manifestações.
3. **Given** o sistema em execução, **When** o usuário pergunta "Qual foi a soma de todas as receitas registradas em 2025?", **Then** a resposta traz o valor calculado a partir dos lançamentos, declara o critério (tipo Receita, competência em 2025) e indica a fonte.
4. **Given** uma resposta exibida, **When** o usuário observa a tela, **Then** vê o domínio, o agente, as fontes e o identificador de rastreio da requisição.

---

### User Story 2 - Respostas seguras: sem invenção, com recusa e esclarecimento (Priority: P1)

Quando a pergunta não tem resposta na base, é ambígua, está fora dos três domínios ou pede algo indevido, o sistema não inventa: informa que não encontrou, pede esclarecimento, explica o escopo ou recusa.

**Why this priority**: Evitar alucinação e vazamento é critério explícito de avaliação e de segurança.

**Independent Test**: Enviar "Existe o protocolo OUV-9999?", "Me diga a senha de outro colaborador", uma pergunta vaga e uma pergunta sobre assunto alheio (ex.: previsão do tempo).

**Acceptance Scenarios**:

1. **Given** um protocolo inexistente, **When** o usuário o consulta, **Then** a resposta diz que não foi encontrado e não apresenta dados inventados.
2. **Given** um pedido de senha de outra pessoa, **When** enviado, **Then** o sistema recusa e orienta o canal autorizado (segurança/privacidade).
3. **Given** uma pergunta ambígua ou de baixa confiança, **When** enviada, **Then** o sistema pede esclarecimento em vez de escolher um domínio.
4. **Given** uma pergunta fora dos três domínios, **When** enviada, **Then** o sistema explica que só cobre financeiro, informações internas e ouvidoria.
5. **Given** uma pergunta sobre dados individuais (ex.: holerite, saldo de férias de alguém), **When** enviada, **Then** o sistema informa que não tem acesso a registros pessoais e encaminha ao RH.

---

### User Story 3 - Execução reproduzível a partir do repositório (Priority: P1)

Um avaliador clona o repositório, copia o arquivo de exemplo de variáveis de ambiente, segue o README e coloca a aplicação para funcionar com um único comando de subida, com as bases já carregadas.

**Why this priority**: O desafio exige explicitamente que o clone funcione seguindo as instruções.

**Independent Test**: Em máquina limpa, executar o passo a passo do README e fazer uma pergunta pela interface.

**Acceptance Scenarios**:

1. **Given** um clone limpo e variáveis configuradas, **When** o avaliador sobe o ambiente conforme o README, **Then** a interface responde e as três bases estão disponíveis sem passos manuais adicionais.
2. **Given** o ambiente já iniciado, **When** a carga de dados roda novamente, **Then** não há duplicação nem erro.

---

### User Story 4 - Rastrear cada interação (Priority: P2)

Quem avalia ou mantém o sistema consegue, para qualquer pergunta, ver o que foi decidido: domínio previsto, confiança, agente escolhido, fontes consultadas, latência, status e erro, a partir de um identificador único de rastreio.

**Why this priority**: Rastreabilidade das execuções é critério de avaliação e princípio da constituição.

**Independent Test**: Fazer uma pergunta, copiar o identificador exibido e localizar o registro correspondente no log com todos os campos.

**Acceptance Scenarios**:

1. **Given** uma pergunta respondida, **When** se consulta o log pelo identificador, **Then** o registro contém timestamp, pergunta, domínio, confiança, agente, fontes, latência e status.
2. **Given** uma falha (ex.: dependência indisponível), **When** ocorre, **Then** o usuário recebe mensagem clara e o log registra o erro com o mesmo identificador.

---

### User Story 5 - Avaliar a qualidade com a suíte AV-T001–AV-T012 (Priority: P2)

O desenvolvedor executa, de forma automatizada, os 12 casos de avaliação e obtém um relatório de aprovação/reprovação por caso (domínio esperado vs. obtido, fonte, critério e latência).

**Why this priority**: Dá evidência objetiva do funcionamento e alimenta a documentação da entrega.

**Independent Test**: Rodar a avaliação e conferir o relatório gerado com 12 linhas.

**Acceptance Scenarios**:

1. **Given** o sistema configurado com um provedor de LLM real, **When** a avaliação é executada, **Then** é gerado um log com o resultado de cada um dos 12 casos.
2. **Given** apenas testes de lógica, **When** são executados sem acesso a LLM real nem rede, **Then** passam de forma determinística.

---

### Edge Cases

- Pergunta vazia, muito longa ou só com símbolos.
- Pergunta que mistura domínios (ex.: reembolso como política e como lançamento).
- Protocolo com formato inválido (ex.: "OUV-12") ou em minúsculas.
- Período sem lançamentos, mês inexistente ou ano fora de 2025–2026.
- Pergunta financeira sem período (ex.: "Qual o total de despesas?"): o sistema pede o período.
- Pergunta financeira sem critério explícito (gasto: pago ou incorrido; competência ou vencimento).
- Tentativa de prompt injection na pergunta ou no conteúdo recuperado (ex.: "ignore as instruções anteriores").
- Provedor de LLM indisponível, lento ou sem chave configurada.
- Banco de dados indisponível ou ainda não carregado.
- Caracteres acentuados e arquivos com marca de ordem de bytes.
- Pergunta sobre status "Respondido" vs. "Concluído" e data de abertura vs. data de resposta.

## Requirements *(mandatory)*

### Functional Requirements

**Orquestração**
- **FR-001**: O sistema MUST receber uma pergunta em texto livre em português e devolver uma resposta, o domínio previsto, o agente escolhido, a confiança, as fontes e um identificador único de rastreio.
- **FR-002**: O sistema MUST classificar cada pergunta em um de: financeiro, informações internas, ouvidoria, ambígua ou fora de escopo.
- **FR-003**: Perguntas de baixa confiança ou ambíguas MUST resultar em pedido de esclarecimento, sem atribuir domínio arbitrário.
- **FR-004**: Perguntas fora de escopo MUST resultar em explicação de que apenas os três domínios são cobertos.
- **FR-005**: Quando a pergunta cruzar domínios, o sistema MUST pedir esclarecimento ao usuário sobre qual domínio responder, sem combinar agentes.

**Agente de informações internas**
- **FR-006**: MUST responder somente com base nos documentos internos e no FAQ, citando o arquivo-fonte.
- **FR-007**: MUST respeitar os limites descritos nos documentos: não confirmar saldos individuais, não consultar holerite, não interpretar casos trabalhistas, não revelar dados de terceiros; encaminhar casos individuais ao canal indicado (ex.: RH).
- **FR-008**: Valores e prazos citados (ex.: 30 dias, 10 dias corridos, alçadas de compra) MUST coincidir com o texto dos documentos.

**Agente de ouvidoria**
- **FR-009**: MUST buscar protocolo por correspondência exata (formato `OUV-NNNN`) e nunca inventar protocolo; sem correspondência, informar que não foi encontrado.
- **FR-010**: MUST permitir consultas por status, categoria, prioridade, canal e intervalo de data de abertura, e responder contagens e listas dessas consultas. Listas MUST mostrar no máximo 10 itens e sempre informar o total, orientando como refinar o filtro quando houver mais.
- **FR-011**: MUST responder perguntas de referência (ex.: lista de status, categorias, prioridades válidas) usando somente os valores enumerados na base de referência.
- **FR-012**: MUST diferenciar data de abertura de data de resposta e "Respondido" de "Concluído", e tratar o prazo de 10 dias como parâmetro demonstrativo, não prazo legal.
- **FR-013**: MUST NOT inferir a identidade de manifestantes.

**Agente financeiro**
- **FR-014**: MUST calcular totais, comparações e indicadores (receita, despesas, execução orçamentária, inadimplência) de forma determinística a partir dos lançamentos e do orçamento, nunca por estimativa do modelo de linguagem.
- **FR-015**: MUST declarar na resposta o critério aplicado (tipo, status, tipo de data, período, centro de custo/departamento).
- **FR-016**: MUST aplicar as regras: despesa paga = tipo Despesa e status Pago; despesa incorrida = todos os status; não confundir competência com vencimento.
- **FR-017**: Quando a pergunta não especificar o critério de "gasto", o sistema MUST assumir despesa **incorrida**, sempre declarando essa interpretação na resposta.
- **FR-018**: Valores monetários MUST ser tratados com precisão decimal exata e exibidos em reais.
- **FR-019**: O modelo de linguagem MUST NOT gerar consultas executáveis sobre os dados; o acesso aos dados MUST ocorrer apenas por consultas predefinidas e parametrizadas, restritas aos domínios permitidos.

**Dados**
- **FR-020**: As bases tabulares (lançamentos, orçamento, manifestações) MUST ser carregadas em banco relacional, validando datas e valores enumerados (tipo, status, prioridade, categoria) e convertendo valores monetários para decimal.
- **FR-021**: Os documentos internos e o FAQ MUST ser indexados com metadados de domínio, fonte e versão do documento, para recuperação dos trechos relevantes.
- **FR-022**: A carga de dados MUST ser repetível sem duplicar registros.
- **FR-023**: Os arquivos em `data/` MUST NOT ser modificados. Nos documentos do projeto, os casos de avaliação são referidos como `AV-T001`–`AV-T012` (correspondentes a `T001`–`T012` no JSON), para não confundir com os IDs de tarefas do `tasks.md`.

**Interface**
- **FR-024**: MUST haver uma página de chat simples onde o usuário digita a pergunta e vê resposta, domínio/agente, fontes e identificador de rastreio, além de mensagens claras de erro e estado de carregamento.

**Rastreabilidade e erros**
- **FR-025**: Cada requisição MUST gerar um registro estruturado com timestamp, identificador de rastreio, pergunta, domínio previsto, confiança, agente, fontes/IDs consultados, latência, status e erro, sem dados pessoais nem segredos.
- **FR-026**: Falhas de dependências (provedor de LLM, banco) MUST resultar em mensagem clara ao usuário e registro do erro, sem interromper o serviço para as demais requisições.
- **FR-027**: Entrada vazia ou inválida MUST ser rejeitada com mensagem apropriada.

**Segurança**
- **FR-028**: Pedidos de credenciais, senhas ou dados de outras pessoas MUST ser recusados com orientação ao canal autorizado.
- **FR-029**: Pergunta do usuário e conteúdo recuperado MUST ser tratados como não confiáveis; instruções embutidas neles MUST NOT alterar o comportamento do sistema.
- **FR-030**: Nenhum segredo (chaves, tokens) MUST ser armazenado no repositório; a configuração sensível vem de variáveis de ambiente, com arquivo de exemplo sem valores reais.

**Avaliação e entrega**
- **FR-031**: MUST existir uma suíte de testes de lógica que roda sem LLM real e sem rede, e um script de avaliação separado que executa AV-T001–AV-T012 com LLM real e gera log de execução por caso.
- **FR-032**: Resultados financeiros esperados MUST ser verificáveis por cálculo independente sobre os arquivos de dados.
- **FR-033**: A entrega MUST incluir README com passo a passo, arquivo de exemplo de variáveis, descrição de arquitetura, decisões, limitações conhecidas e como testar, além do registro contínuo do desenvolvimento.
- **FR-034**: O provedor de LLM padrão MUST ser o Google Gemini. Sem chave configurada, o sistema MUST operar em modo degradado, roteando por regras/palavras-chave e avisando a degradação ao usuário.
- **FR-035**: Quando uma pergunta financeira não informar o período, o sistema MUST pedir esclarecimento sobre o período, sem assumir intervalo.
- **FR-036**: Para "receita líquida", como a base não contém deduções registradas, o sistema MUST responder com o total das receitas e declarar que não há deduções registradas (líquida igual à soma das receitas).
- **FR-037**: A execução orçamentária MUST usar despesas pagas quando a pergunta não especificar o critério, porque o indicador é definido como "despesas realizadas ÷ orçamento aprovado do mesmo período e centro de custo"; a resposta MUST declarar o critério.
- **FR-038**: A inadimplência de recebíveis MUST ser calculada em valor (receitas com status Atrasado ÷ total de receitas do período), declarando o critério na resposta.

### Key Entities

- **Pergunta**: texto livre do usuário, com identificador de rastreio atribuído na entrada.
- **Classificação**: resultado do orquestrador — domínio previsto (ou ambígua/fora de escopo) e confiança.
- **Resposta**: texto final, agente que atendeu, fontes citadas e status.
- **Fonte**: referência verificável (nome de arquivo, ID de lançamento, protocolo).
- **Registro de interação (log)**: evento estruturado de uma requisição, ligado pelo identificador de rastreio.
- **Lançamento financeiro**: receita ou despesa com competência, vencimento, categoria, centro de custo, departamento, contraparte, valor e status.
- **Orçamento mensal**: valor aprovado por mês, ano e centro de custo.
- **Manifestação de ouvidoria**: protocolo, datas, categoria, assunto, canal, prioridade, status, área responsável, resumo e resposta.
- **Documento interno**: política ou procedimento com versão, seções e limites de resposta; **item de FAQ** relacionado a um documento.
- **Caso de avaliação**: pergunta, domínio esperado, fonte esperada e critério (AV-T001–AV-T012).

## Decisões da seção 8 do briefing *(todas resolvidas)*

1. **Provedor de LLM e chave:** Google Gemini (`gemini-3.1-flash-lite`); sem chave, roteamento por regras com aviso (FR-034; Clarifications).
2. **Recuperação para documentos internos:** BM25 em memória (`research.md` §1).
3. **Framework de agentes:** LangGraph, só para o grafo de orquestração (`research.md` §2; constituição 1.2.0).
4. **Perguntas que cruzam domínios:** pedido de esclarecimento, sem combinar agentes (FR-005).
5. **Interpretação padrão de "gasto":** despesa incorrida, sempre declarada (FR-017).
6. **Formato das fontes:** `{tipo, ref, detalhe}` com arquivo, protocolo, lançamento ou consulta (`research.md` §3).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Nos 12 casos de avaliação, 100% são direcionados ao domínio esperado e 100% das respostas satisfazem o critério de cada caso.
- **SC-002**: 100% das respostas das perguntas sobre informações internas e ouvidoria citam ao menos uma fonte verificável; 100% das respostas financeiras declaram o critério usado.
- **SC-003**: Os valores financeiros de AV-T006, AV-T007 e AV-T011 coincidem exatamente (centavo) com o cálculo independente sobre os arquivos.
- **SC-004**: Em protocolos inexistentes, pedidos de credenciais e perguntas fora de escopo, 0 respostas apresentam dado inventado ou credencial.
- **SC-005**: Um avaliador, em máquina limpa, coloca a aplicação no ar e obtém a primeira resposta em até 15 minutos seguindo apenas o README.
- **SC-006**: 100% das requisições têm um registro correspondente localizável pelo identificador exibido ao usuário.
- **SC-007**: Em condições normais, a resposta aparece em até 10 segundos em pelo menos 90% das perguntas.
- **SC-008**: Os testes de lógica rodam sem rede e passam em 100% das execuções repetidas.

## Assumptions

- Os dados são sintéticos (empresa fictícia Aurora, 2025-01 a 2026-12) e o sistema não precisa tratar dados pessoais reais.
- Um único perfil de usuário (colaborador), sem autenticação, sem multiusuário e sem escrita nas bases.
- A interface e as respostas são em português do Brasil.
- Cada pergunta é tratada de forma independente; conversa com memória entre turnos é desejável, não obrigatória.
- Uso interno de baixa concorrência (demonstração/avaliação).
- O critério "paga vs. incorrida" para consultas explícitas segue as regras de `indicadores_e_regras.json`.
- Há acesso a um provedor de LLM e a uma chave para a avaliação com LLM real; os testes de lógica não dependem disso.
- Implementação em fases, com aprovação explícita entre elas (constituição, princípio IX). O fatiamento em fases será definido no plano.
- As restrições técnicas (Python/FastAPI, HTML/CSS/JS simples, PostgreSQL, Docker) vêm do desafio e da constituição e serão tratadas no plano.
