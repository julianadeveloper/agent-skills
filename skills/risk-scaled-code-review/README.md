# Risk-Scaled Code Review

Skill de code review para agentes (Cursor / Claude / Windsurf / opencode) que
**escala a profundidade com o risco do diff** e só publica achados com evidência
(confiança ≥ 80). Funciona em qualquer repositório: o núcleo é
**diff + acoplamento + bugs/regressões**. Governança e ticket entram
só se existirem.

| | |
|---|---|
| Identificador | `risk-scaled-code-review` |
| Versão | `1.3.1` |
| Licença | CC-BY-4.0 |

A instrução completa está em [`SKILL.md`](./SKILL.md) — este README só cobre
instalação e uso rápido.

---

## Instalação

Copie (ou faça submodule/subtree) a pasta da skill para o destino que o agente lê:

```text
seu-repo/
└── .cursor/skills/risk-scaled-code-review/
    ├── SKILL.md
    ├── README.md
    ├── assets/finding.schema.json
    ├── references/          # checklists, prompts, formato de entrega
    └── scripts/             # triage determinístico
```

Alternativas: `.claude/skills/`, `.agents/skills/`, `.opencode/skills/` — mesma
árvore interna.

**Pré-requisitos:** Python 3 (triage), `git` (diff local), `gh` **ou** MCP GitHub
(PR remoto / postar comentário). Jira e `AGENTS.md` são opcionais.

### Smoke test

```bash
SKILL=.cursor/skills/risk-scaled-code-review
python3 "$SKILL/scripts/triage.py" --range origin/main...HEAD
```

Se imprimir JSON com `tier` / `specialists`, a instalação está ok.

---

## Como usar

| Pedido | O que acontece |
|--------|----------------|
| `Revisa esse PR` + URL/número | Diff remoto → triage → review completa |
| `Review origin/main...HEAD` | Diff local → mesmo fluxo |
| `Review crítico / profundo` | Força tier `deep` |
| `Review completo` / `incluir sugestões` | Inclui 🟢 na entrega |
| `Posta o comentário no PR` | Só após você confirmar; usa `gh pr comment` |

A skill dispara sozinha quando o pedido menciona review de PR/diff, regressão,
auth, dados ou risco de merge (`SKILL.md` description).

---

## Mapa de arquivos

| Path | Papel |
|------|--------|
| `SKILL.md` | Fluxo que o agente executa |
| `scripts/triage.py` | Decide tier + especialistas |
| `assets/finding.schema.json` | Schema dos achados internos |
| `references/checklists-core.md` | Checks genéricos + fluxo cross-repo |
| `references/subagentes.md` | Sinais→especialistas + prompts |
| `references/entrega.md` | Classificação 🔴/🟡/🟢 + PIA + veredito + métricas |

---

Autoria: Juliana Oliveira · Licença: **CC-BY-4.0**
