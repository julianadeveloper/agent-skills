# Jira Task Writer

Skill para agentes (Cursor / opencode / Claude) que **cria e lê tasks no Jira**
com template estruturado — legível por humanos **e** agents — e busca a
**wave (sprint ativo)** para contexto antes de criar.

| | |
|---|---|
| Identificador | `jira-task-writer` |
| Versão | `1.0.0` |
| Licença | CC-BY-4.0 |

---

## O que faz

- **Lê** tasks do Jira (chave, link ou "essa task X").
- **Busca a wave** = sprint ativo do board/projeto para contexto e detecção de
  duplicidade.
- **Cria** tasks com template por tipo: `Tarefa`, `Bug`, `História`, `Operação`.
- Template: **Problema**, **Solução**, **Cenários de Testes**, **DoD** +
  **Dependências** (link real entre tasks) e **Review Externo** (a skill
  pergunta quando necessário).

## Pré-requisitos

| Dependência | Quando |
|-------------|--------|
| MCP de Jira (qualquer servidor) | Sempre — a skill descobre as tools sozinha |
| Acesso ao sprint ativo via MCP | Para o contexto da wave |

Sem MCP de Jira, a skill **degrade** (avisa e não cria nada). Exemplo de MCP
no `opencode.json`:

```json
{
  "mcp": {
    "atlassian": {
      "type": "local",
      "command": ["npx", "-y", "@atlassian/mcp@latest"],
      "environment": {
        "ATLASSIAN_SITE_URL": "{env:ATLASSIAN_SITE_URL}",
        "ATLASSIAN_USER_EMAIL": "{env:ATLASSIAN_USER_EMAIL}",
        "ATLASSIAN_API_TOKEN": "{env:ATLASSIAN_API_TOKEN}"
      }
    }
  }
}
```

(Pode usar qualquer outro servidor MCP de Jira — a skill é agnóstica.)

## Instalação

Copie a pasta para o destino que o agente lê:

```text
seu-repo/
└── .cursor/skills/jira-task-writer/
    ├── SKILL.md
    ├── README.md
    └── references/template.md
```

Ou em opencode, aponte via `skills.paths`. Reinicie o agente depois.

## Como usar

| Pedido | O que acontece |
|--------|----------------|
| "Cria uma task no Jira para ..." | Descobre MCP → busca a wave → pergunta o essencial → cria no template |
| "Abre um bug: <descrição>" | Usa o template de Bug (passos, esperado vs atual, ambiente, impacto) |
| "Escreve uma história para ..." | Template de História (aceite, valor/escopo) |
| "Vê essa task PROJ-123" | Lê e resume a task |
| "Tem algo parecido na wave?" | Busca o sprint ativo e aponta duplicidade/relações |

## Mapa de arquivos

| Path | Papel |
|------|--------|
| `SKILL.md` | Fluxo: descobrir MCP → ler → wave → criar → verificar |
| `references/template.md` | Template base + ajustes por tipo (Bug/História/Operação) |

---

Autoria: Juliana Oliveira · Licença: **CC-BY-4.0**
