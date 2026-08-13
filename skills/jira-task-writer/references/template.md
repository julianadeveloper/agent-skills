# Template de task Jira

Estrutura-base aplicada a **todos** os tipos (descrição em Markdown, títulos `##`).

## Template base

```markdown
## Problema

O que está errado / contexto / motivação (1–3 frases objetivas).
Referencie a task ou incidente que motivou, se houver (chave/link).

## Solução

Abordagem proposta (passos ou descrição).
Alternativas consideradas, se relevante (1 linha cada).

## Cenários de Testes

| Cenário | Pré-condição (Given) | Ação (When) | Resultado esperado (Then) |
|---------|----------------------|-------------|---------------------------|
| Happy path | estado inicial | ação | resultado principal |
| Borda/validação | dado inválido | ação | erro tratado |
| Erro | falha externa | ação | fallback/mensagem |
| Regressão | caso antigo | ação | comportamento preservado |

Cubra: happy path, validação/borda, erro, regressão.

## Definition of Done (DoD)

Checklist verificável por outra pessoa/agente sem conversa adicional:

- [ ] Critério 1 (ação mensurável)
- [ ] Critério 2
- [ ] Testes acima passando

## Dependências

- Bloqueada por: `PROJ-123`
- Bloqueia: `PROJ-456`
- Relacionada: `PROJ-789`
- (se não houver: "Nenhuma")

## Review Externo

- Necessário: Sim / Não
- Quem: @squad / pessoa
- O quê: (produto, segurança, arquitetura, design)
```

---

## Ajustes por tipo

### Tarefa

Uso: implementação pequena/média com solução conhecida.
Usa **apenas o template base**.

### Bug

Adiciona ao base:

```markdown
## Passos para Reproduzir

1. Passo 1
2. Passo 2

## Comportamento Esperado vs Atual

- Esperado: ...
- Atual: ...

## Ambiente

Versão / ambiente / feature flag.

## Impacto

Quem/quantos afetados e severidade.
```

### História (Story)

Uso: funcionalidade com valor de negócio. Adiciona ao base:

```markdown
## Critérios de Aceite

- [ ] Given/When/Then (cenário de aceite principal)
- [ ] Given/When/Then (cenário complementar)

## Valor / Escopo

- Para quem e qual valor.
- Fora de escopo: ...
```

### Operação

Uso: runbook/procedimento (deploy, manutenção, dados). Adiciona ao base:

```markdown
## Procedimento

1. Passos para executar

## Janela / Momento

Quando pode rodar (janela de manutenção, horário).

## Rollback

Como reverter se algo der errado.

## Quem Executa / Monitoramento

Responsável e como acompanhar (dashboard, log, alerta).
```

---

## Regras de escrita

- **Título:** curto e acionável (imperativo), ex.: "Adicionar normalização de
  e-mail no update".
- **Cenários de teste:** dados concretos, estados e bordas; nunca "testar bem".
- **DoD:** verificação objetiva que não depende de quem lê.
- **Dependências:** sempre por **chave real** vinculada (não texto solto).
- **Review externo:** só preencher "Necessário: Sim" quando houver área fora do
  squad envolvida; nesse caso indicar quem e o quê.
