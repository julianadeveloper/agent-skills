# Risk-Scaled Code Review

Skill de code review para agentes (Cursor / Claude) que **escala a profundidade
com o risco do diff** e só publica achados com evidência (confiança ≥ 80).

Funciona em qualquer repositório: o núcleo é **diff + acoplamento + bugs/regressões**.
Governança, ticket e graphify entram só se existirem.

| | |
|---|---|
| Identificador | `risk-scaled-code-review` |
| Versão | `1.3.1` |
| Licença | CC-BY-4.0 |

---

## Instalação no repositório

Copie (ou faça submodule/subtree) a pasta da skill para o destino que o agente lê:

```text
seu-repo/
└── .cursor/skills/risk-scaled-code-review/
    ├── SKILL.md                 # instruções do agente (obrigatório)
    ├── README.md                # este guia
    ├── assets/
    │   └── finding.schema.json
    ├── references/              # checklists, prompts, formato de entrega
    └── scripts/                 # triage e blast (graphify)
```

Alternativas comuns: `.claude/skills/`, `.agents/skills/` — mantenha a mesma
árvore interna.

**Pré-requisitos no ambiente do desenvolvedor / CI:**

| Dependência | Quando |
|-------------|--------|
| Python 3 | Sempre (triage; query_graph só se houver graphify) |
| `git` | Diff local |
| `gh` **ou** MCP GitHub | Review de PR remoto / postar comentário |
| `GH_HOST` / `GITHUB_API_URL` | Só se GitHub Enterprise (REST direto) |

Não precisa de graphify, Jira nem `AGENTS.md` para a skill rodar.

### Smoke test após instalar

Na raiz do **repo sob review** (não necessariamente dentro da pasta da skill):

```bash
# Ajuste o path se a skill estiver em .cursor/skills/...
SKILL=.cursor/skills/risk-scaled-code-review

python3 "$SKILL/scripts/triage.py" --range origin/main...HEAD
python3 "$SKILL/scripts/query_graph.py" --detect-only
```

Se o triage imprimir JSON com `tier` / `specialists`, a instalação está ok.

---

## Como usar

### No chat do agente

| Pedido | O que acontece |
|--------|----------------|
| `Revisa esse PR` + URL ou número | Diff remoto → triage → review completa |
| `Review origin/main...HEAD` | Diff local → mesmo fluxo |
| `Review crítico / profundo` | Força tier `deep` |
| `Review completo` / `incluir sugestões` | Inclui 🟢 na entrega |
| `Posta o comentário no PR` | Só após você confirmar; usa `gh pr comment` |

A skill também dispara sozinha quando o pedido menciona review de PR/diff,
regressão, auth, dados ou risco de merge (`SKILL.md` description).

### Via comandos (alternativa aos scripts, útil para debug)

```bash
# 1) Diff (gh primeiro; MCP é fallback)
git diff --no-color -U1 origin/main...HEAD -- . ':!*.lock' ':!package-lock.json' ':!yarn.lock' ':!pnpm-lock.yaml' ':!composer.lock' ':!Gemfile.lock' ':!poetry.lock' ':!dist/**' ':!build/**' ':!*.min.js' ':!*.min.css'
gh pr view 123 --repo owner/repo
gh pr diff 123 --repo owner/repo

# 2) Triage (decide tier + especialistas)
python3 "$SKILL/scripts/triage.py" --range origin/main...HEAD
python3 "$SKILL/scripts/triage.py" --range origin/main...HEAD --force-tier deep

# 3) Blast radius (só se graphify existir; senão use o tool Grep)
python3 "$SKILL/scripts/query_graph.py" --detect-only
python3 "$SKILL/scripts/query_graph.py" caminho/ou/Simbolo

# 4) Postar no PR (só com confirmação humana)
gh pr comment 123 --repo owner/repo --body-file review.md
```

Filtro de achados (threshold ≥80 / dedupe) é aplicado inline pelo agente — não há script.

---

## Como funciona

```text
ENTRADA → TRIAGE → CONTEXTO → INVESTIGAR → JULGAR → FILTRAR → ENTREGAR
```

1. **Entrada** — obtém o diff (PR, range ou colado); descobre se o repo tem
   governança / ticket / graphify.
2. **Triage** — `triage.py` escolhe o **tier** e quais **especialistas** rodam
   (security, data, async, observability) a partir do tamanho e dos sinais no diff.
3. **Contexto** — intenção + hunks + **blast radius** (graphify quando existe,
   senão Grep) + **cross-repo** se o contrato front↔back for tocado
   (`references/checklists-core.md` §6; pergunta o companion se desconhecido).
4. **Investigar** — checklists core + especialistas do plano; foco em regressão,
   contrato quebrado e acoplamento.
5. **Julgar** — 7 critérios de elegibilidade; score de confiança 0–100.
6. **Filtrar** — só publica confiança ≥ **80** (inline, sem script).
7. **Entregar** — comentário no formato PIA + veredito.

### Tiers

| Tier | Quando (default) | Comportamento |
|------|------------------|---------------|
| `lite` | Poucos arquivos/linhas, sem sinal crítico | Review inline, sem subagentes |
| `standard` | Caso típico | Core + especialistas acionados + juiz |
| `deep` | Diff grande, hint crítico, ou alto risco | Pipeline completo + blast obrigatório |
| `split` | Diff enorme (>~40 arquivos ou >~1500 linhas) | Pede quebra do PR; não revisa tudo |

Limiares exatos: `SKILL.md` (Passo 1) e `scripts/triage.py`.

### Graphify — quando usar

Graphify **não é obrigatório**. Ele só dá um diferencial: acoplamento **transitivo**
(A→B→C), que o Grep não vê. O triage detecta sozinho:

- `graphify_available: true` (ex.: existe `graphify-out/graph.json`) →
  `python3 scripts/query_graph.py <simbolo>` para blast.
- Senão → use o tool **Grep** em imports/call sites e declare
  *aproximação grep — sem acoplamento transitivo*.

Se o repo não mantém export de grafo, ignore graphify — Grep cobre o caso.

### Severidade na entrega

| Severity interna | Entrega | Bloqueia merge? |
|------------------|---------|-----------------|
| `critical` / `high` | 🔴 Crítico | Sim |
| `medium` | 🟡 Bloqueante | Precisa resposta/correção |
| `low` | 🟢 Sugestão | Não |

**Modo bot** (default ao postar no PR): omite 🟢.  
**Modo completo**: inclui 🟢 se você pedir.

### O que a skill analisa (e o que não)

**Analisa:** bugs/regressões introduzidos pelo diff, contrato assimétrico
(create vs update, reader vs writer, **front ↔ back**), acoplamento
(callers/consumidores), gaps de teste **concretos**, segurança/dados/async
quando o diff aciona o sinal.

**Não comenta:** estilo isolado, nit, preexistente, “faltam testes” genérico,
o que linter/CI já pega, achado sem evidência.

---

## O que a entrega parece

Ordem fixa:

1. Contexto + tier (+ motivo se `deep`/`split`) + degradações (ex.: sem graphify)
2. Raio de impacto
3. Achados 🔴 → 🟡 → 🟢 (se completo), cada um em **PIA**:
   - **Problema** → **Impacto** → **Ação**
4. Perguntas em aberto
5. Veredito (aprovar / com ressalvas / solicitar alterações / não revisar)
6. Métricas internas (publish / hold / discard)

Formato, classificação e veredito: `references/entrega.md`.

---

## Adaptar ao seu repositório (opcional)

| Recurso | Efeito |
|---------|--------|
| `AGENTS.md`, constitution, ADRs, `.cursor/rules/` | Ativa `policy-reviewer` nas regras **relevantes ao diff** |
| Graphify (`graphify-out/graph.json` etc.) | Blast radius com acoplamento transitivo; senão usa Grep |
| Repo/path companion (front ou back) | Spot-check de contrato cross-repo quando o triage marca o sinal |
| PR/issue/ticket (ou Jira MCP) | Melhora intenção antes/depois |
| `references/checklists-domain-<produto>.md` | Overlay de domínio; só aplica se o gatilho do arquivo casar |

Checklist genérico obrigatório: `references/checklists-core.md`.  
Overlays de domínio: `references/checklists-domain-<produto>.md` (aplica só se o gatilho casar).

---

## Mapa de arquivos

| Path | Papel |
|------|--------|
| `SKILL.md` | Fluxo que o agente executa |
| `scripts/triage.py` | Decide tier + especialistas + detecta graphify |
| `scripts/query_graph.py` | Blast radius via graphify (opcional) |
| `assets/finding.schema.json` | Schema dos achados internos |
| `references/checklists-core.md` | Checks genéricos + fluxo cross-repo |
| `references/subagentes.md` | Sinais→especialistas + prompts dos investigadores |
| `references/entrega.md` | Classificação 🔴/🟡/🟢 + template PIA + veredito + métricas |

---

## Glossário rápido

| Termo | Significado |
|-------|-------------|
| **Tier** | Profundidade: lite / standard / deep / split |
| **Blast radius** | Quem quebra se o contrato/função mudou |
| **Confiança** | 0–100; publicar só ≥ 80 |
| **Hold** | 60–79 — fica em métrica interna, não no comentário ao autor |
| **PIA** | Problema → Impacto → Ação |
| **Degradação** | Declarar na entrega quando falta graphify, governança ou ticket |

---

Autoria: Juliana Oliveira · Licença: **CC-BY-4.0**
