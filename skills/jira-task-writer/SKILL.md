---
name: jira-task-writer
description: >-
  Cria e lê tasks no Jira com template estruturado (Problema, Solução, Cenários
  de Testes, DoD, Dependências, Review Externo) legível por humanos e agents.
  Busca a wave (sprint ativo) para contexto e evita duplicidade. Cria Tarefa,
  Bug, História e Operação. Use quando pedirem criar task no Jira, abrir bug,
  escrever história, documentar DoD, checar a sprint/wave atual ou entender
  contexto de uma task existente.
---

# Jira Task Writer

Cria e lê tasks no Jira com template estruturado — **legíveis por humanos e
agentes**. Busca a wave (sprint ativo) para contexto e evita duplicidade.

## Dependências de runtime

| Dependência | Obrigatória? | Uso |
|-------------|--------------|-----|
| MCP de Jira (qualquer servidor) | Sim | ler / buscar / criar issues |
| Sprint ativo (wave) acessível via MCP | Sim | contexto antes de criar |

Sem MCP de Jira configurado → **degrade**: avise que não há MCP e peça a
configuração; **não crie** nada "de memória".

## Princípios

1. **Task boa para agents = contexto mínimo suficiente** — outra pessoa ou
   agente executa sem conversa adicional.
2. **Leia antes de criar** — wave/sprint + tasks parecidas → sem duplicidade e
   com contexto real.
3. **Template sempre** — seções opcionais entram só quando aplicáveis.
4. **Pergunte o que faltar** — projeto, dependência, review externo. Não invente.
5. **Verifique depois de criar** — releia a task e confirme campos e links.

## Fluxo

### Passo 0 — Descobrir o MCP

- Liste as ferramentas do MCP de Jira disponíveis (o servidor pode se chamar
  `atlassian`, `jira`, `jira_mcp`, etc. — descubra no ambiente).
- Mapeie por função: **ler issue**, **buscar por JQL/sprint**, **criar issue**,
  **vincular/relacionar issues**, **listar projetos**.
- Use os nomes reais das tools; não presuma.

**Done quando:** tools mapeadas (ou degradação declarada se não houver MCP).

### Passo 1 — Ler a task (se informada)

- O usuário pode citar "essa task X", uma chave (ex.: `PROJ-123`) ou um link.
- Leia: resumo, descrição, tipo, status, sprint, prioridade, links de
  dependência.

**Done quando:** contexto da task lido ou explicitamente ausente.

### Passo 2 — Wave = sprint ativo (contexto)

- Busque as issues do **sprint ativo** do board/projeto (JQL aproximado:
  `sprint in openSprints() AND project = <KEY>`, ou a tool de sprint do MCP).
- Use para:
  - **Detectar duplicidade** — task parecida já existe? Ajuste ou avise.
  - Entender o **escopo atual** da wave.
  - Encontrar **tasks relacionadas/dependentes** (candidatas a link).

**Done quando:** contexto da wave coletado e checado contra a task a criar.

### Passo 3 — Criar a task

1. **Pergunte o essencial que faltar:** projeto (chave), tipo, resumo/título,
   sprint (se não for a wave atual).
2. **Tipo → template:** escolha o modelo em
   `references/template.md` conforme o tipo (`Tarefa` | `Bug` | `História` |
   `Operação`).
3. **Dependências:** se houver task dependente, peça a **chave** para vincular
   de verdade (não texto solto). Se a dependência for de outra task ainda não
   criada ou de outra pessoa, **pergunte** como registrar.
4. **Review externo:** se o trabalho tocar área fora do squad (segurança,
   produto, arquitetura, design), **pergunte** se é necessário e quem/o quê.
5. **Confirme o plano** com o usuário (projeto, tipo, título e o resumo do
   template) **antes** de criar.
6. Crie via MCP: issue type, summary, description (Markdown no template),
   priority, labels, sprint e links quando a tool permitir.

**Done quando:** task criada com descrição no template e links aplicados.

### Passo 4 — Verificar e reportar

- Releia a task criada: tipo, projeto, sprint, prioridade e dependências
  vinculadas.
- Reporte a **chave/link** criado e um resumo de 1–2 linhas.

**Done quando:** criação conferida e chave entregue ao usuário.

## Boas práticas

- Descrição com **Markdown e títulos** (o template usa `##`).
- **Cenários de teste com dados concretos** e bordas (happy path, validação,
  erro, regressão).
- **DoD verificável por terceiros** — ações mensuráveis, não "está pronto".
- **Links reais de dependência** (nunca chave solta em texto).
- Título curto e acionável.
- Prefira perguntar a supor quando o resultado depende de decisão de produto
  ou de outra área.

## Perguntas que a skill pode fazer

| Situação | Pergunta |
|----------|----------|
| Sem chave de projeto | "Qual projeto/chave Jira?" |
| Sem resumo claro | "Qual o título da task?" |
| Task dependente existe | "Qual a chave da task que bloqueia/é bloqueada?" |
| Dependência de outra área ainda não criada | "Crio a task dependente também, ou só registro a dependência?" |
| Toque fora do squad | "Precisa de review externo (produto/segurança/arquitetura)? De quem?" |
| Duplicidade detectada na wave | "A task X já cobre isso — devo reaproveitar ou criar nova?" |
