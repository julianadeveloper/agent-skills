# agent-skills

Coleção de skills para agentes de IA (Cursor / opencode / Claude).

Cada skill vive em `skills/<identificador>/` e segue a convenção `SKILL.md`
(instruções do agente) + `references/` + `scripts/` opcionais.

## Skills

| Skill | Identificador | O que faz | Versão |
|-------|---------------|-----------|--------|
| [Risk-Scaled Code Review](skills/risk-scaled-code-review/) | `risk-scaled-code-review` | Review de PR/diff que escala a profundidade com o risco (tiers lite/standard/deep/split), blast radius, especialistas sob demanda e publicação só com confiança ≥80. | 1.3.0 |

## Instalação

Copie a pasta da skill desejada para o destino que o agente lê:

```text
seu-repo/
└── .cursor/skills/risk-scaled-code-review/
```

Ou, em opencode, aponte via `skills.paths` no `opencode.json`. Ver o README
de cada skill para pré-requisitos e smoke test.

---

Licença: **CC-BY-4.0** · Autoria: Juliana Oliveira
