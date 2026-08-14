---
name: risk-scaled-code-review
description: >-
  Code review que escala com o risco (tiers lite/standard/deep/split):
  triage determinístico, blast radius (grep), análise de acoplamento e
  regressão, especialistas sob demanda, confiança ≥80, checklists core + overlay
  de domínio opcional, classificação 🔴/🟡/🟢 e veredito coerente. Use quando
  pedirem revisar PR/diff, review crítico, validar regressão,
  auth, dados ou risco de merge. Também use para postar comentários no GitHub
  após confirmação do usuário.
---

# Risk-Scaled Code Review

Review que **escala com o risco**: triage barato, investigação cara, só publica
achado com evidência. O núcleo é **diff + acoplamento + bugs/regressões** — em
qualquer repositório. Governança e ticket entram só se existirem no repo ou
nas ferramentas disponíveis.

> Vocabulário de profundidade: **tier** (`lite` / `standard` / `deep` / `split`).

## Dependências de runtime

| Dependência | Obrigatória? | Uso |
|-------------|--------------|-----|
| `git` | Sim | `git diff` / ranges e hunks |
| Python 3 | Sim | `scripts/triage.py` |
| `gh` | Só PR remoto / postar | `gh pr view`, `gh pr diff`, `gh pr comment` |
| MCP GitHub | Fallback p/ GHE sem token | `pull_request_read` |
| `GH_HOST` / `GITHUB_API_URL` | Opcional (Enterprise) | Base da API se usar REST direto |
| Arquivos de governança no repo | Opcional | Policy-reviewer se existirem |
| Fonte de requisito (PR/issue/Jira/MCP) | Opcional | Intenção da mudança |

Se opcional faltar, declare a degradação na entrega — **não aborte** a review.

## Princípios

1. **Intenção quando houver** — PR/issue/ticket esclarecem mudança deliberada vs regressão; sem isso, derive do diff e do histórico próximo.
2. **Triage barato, investigação cara** — `scripts/triage.py` manda no plano.
3. **Acoplamento sempre** — quem chama / importa / consome o contrato alterado (Grep).
4. **Evidência ou silêncio** — confiança ≥ **80** para publicar.
5. **Minor é sugestão** — `low` → 🟢; não bloqueia merge.
6. **Veredito coerente** — severidade manda, não o tom positivo da direção.

## Fluxo

```
ENTRADA → TRIAGE → CONTEXTO → INVESTIGAR → JULGAR → FILTRAR → ENTREGAR
```

### Passo 0 — Entrada

Aceite URL/número de PR, range local (`base...head`) ou diff colado.

**Obter diff (ordem de preferência):**

1. **Local:** `git diff --no-color -U1 base...head -- . ':!*.lock' ':!package-lock.json' ':!yarn.lock' ':!pnpm-lock.yaml' ':!composer.lock' ':!Gemfile.lock' ':!poetry.lock' ':!dist/**' ':!build/**' ':!*.min.js' ':!*.min.css'` (use `-U3` em deep) +
   `git log --oneline base..head`.
2. **PR remoto:** `gh pr view <n> --repo <owner/repo>` e
   `gh pr diff <n> --repo <owner/repo>`.
3. **Fallback:** MCP GitHub (`pull_request_read`) ou peça o diff ao usuário.
   **Não aborte** a review se falhar.

`-U1` reduz contexto de hunk em tiers baratos — só aumente quando o hunk precisar.

**Discovery de governança** (não assuma paths): procure na raiz e docs do repo
alvo, nesta ordem aproximada — use o que **existir**:

- `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`
- `constitution.md`, `CONSTITUTION.md`, `docs/constitution.md`,
  `.specify/memory/constitution.md` (Speckit — só se o path existir)
- ADRs / `docs/adr/` / `.cursor/rules/` relevantes aos paths do diff

Se **nenhum** arquivo de governança existir: pule policy-reviewer; concentre a
análise em corretude do diff, acoplamento e regressão.

**Intenção:** título/corpo do PR ou issue; ticket na branch; ferramenta de
tracker (ex. Jira MCP) **só se disponível**. Sem requisito externo, reconstrua
antes/depois a partir do diff.

**Done quando:** diff obtido + lista do que existe/não existe (governança,
ticket).

### Passo 1 — Triage (obrigatório)

```bash
# reusa o diff do Passo 0 (não refaça git diff):
git diff --no-color -U1 origin/main...HEAD -- . ':!*.lock' ':!dist/**' ... | python scripts/triage.py --input -
# forçar profundidade:
python scripts/triage.py --input mudanca.diff --force-tier deep
```

Obedeça `tier` e `specialists` do JSON.

| Tier | Quando | Investigação |
|------|--------|--------------|
| `lite` | PR pontual | Inline, sem subagentes: core (+ domain se houver) + especialistas do triage |
| `standard` | Default | Subagentes `diff-reviewer`, `logic-reviewer` + especialistas acionados + juiz |
| `deep` | Alto risco / diff grande | Pipeline completo + blast obrigatório + `test-gap-reviewer`; `policy-reviewer` **só se** houver governança |
| `split` | Diff enorme | Peça quebra; não revise tudo |

**Limiares:** `lines > 1500` ou `files > 40` → `split`; `files ≤ 8` e `lines ≤ 200`
e sem sinal → `lite`; hint crítico **ou** `lines ≥ 600` **ou** `files ≥ 20` **ou**
(≥3 sinais e `lines ≥ 300`) → `deep`; resto → `standard`.

Só suba de tier se o usuário pedir ("review crítico") ou surgirem fatos novos
(migração destrutiva, incidente). Anote o motivo na entrega.

**Done quando:** plano (tier, specialists) fixado e seguido.

### Passo 2 — Contexto mínimo

Monte só o necessário para o tier:

1. **Intenção** — comportamento antes/depois (do ticket ou do diff).
2. **Diff por arquivo** — hunks com contexto; nunca um blob único gigante.
3. **Governança** — só trechos **existentes** e **relevantes aos paths** do diff.
4. **Blast radius** — consumidores/callers do que mudou: **Grep/leitura de
   imports e call sites** (arquivo usado em outro lugar, símbolo renomeado,
   throw/erro que propaga via `Promise.all`/`catch`). Grep acha o acoplamento
   direto; não há grafo transitivo.

Em `deep`, blast é **obrigatório**. Em `standard`, faça blast quando houver
mudança de contrato/API/export ou especialistas `data`/`async`. Em `lite`, faça
blast (grep) apenas se o diff renomear/remover export ou mudar assinatura.

**Cross-repo (front ↔ back):** se triage `needs_cross_repo_check: true` **ou**
o diff tocar contrato de API/payload/auth/evento entre camadas, siga o
`references/checklists-core.md` §6:

1. Identifique o contrato tocado (rota, campo, schema, evento).
2. Se o repo/path companion **não** for conhecido → **pergunte** ao usuário antes de fechar a review (não invente o repo).
3. Faça **spot-check** do companion (não review completa), com evidência nos dois lados.
4. Workspace aberto no companion ajuda, mas **não substitui** este passo — declare degradação se o companion não for acessível.

**Done quando:** intenção + hunks + (governança se houver) + raio de impacto
com fonte (grep) + (cross-repo verificado | perguntado | degradado)
registrados.

### Passo 3 — Investigar

**Checklists a aplicar** (sem leitura de arquivo extra):

| Arquivo | Escopo |
|---------|--------|
| `references/checklists-core.md` | Genérico — normalização, derivados, regra silenciada, escopo, test gap, cross-repo |
| `references/checklists-domain-*.md` | Overlay de domínio — **só se o arquivo existir** e o gatilho casar |

**Subagentes / passada inline:**

- Tier `lite`: leia "Regras comuns" + blocos dos **especialistas do triage**;
  aplique tudo **inline** (sem spawnar subagente).
- Tier `standard` / `deep`: leia "Regras comuns" + os blocos dos
  **especialistas listados pelo triage** (somente eles).

Em ambiente de janela única (Cursor): rode como passada única cobrindo
todos os especialistas acionados — **sem reimprimir o diff por especialista**
(referencie "DIFF já carregado acima").

Foco da análise (sempre, qualquer repo):

- Bugs e regressões **introduzidos ou agravados** pelo diff
- Contrato quebrado pela metade (create vs update, reader vs writer, caller vs callee)
- Acoplamento: callers, imports, filas, schemas, clientes do símbolo/arquivo alterado
- Checklists core cujo gatilho o diff acionar (`references/checklists-core.md`)
- Overlay `references/checklists-domain-*.md` **somente se o arquivo existir** e o
  gatilho do overlay casar com o diff

Retorno interno: JSON conforme `assets/finding.schema.json` — **não publique ainda**.

**Done quando:** todo especialista listado no triage rodou; todo check core com
gatilho no diff foi considerado; blast do passo 2 informado a investigação;
achados só sobre mudança introduzida/agravada.

### Passo 4 — Julgar

Aplique os **7 critérios** (todos obrigatórios):

1. **Causado ou agravado** pela mudança (não preexistente).
2. **Verificável** — código, teste, histórico ou consumidor real.
3. **Impacto concreto** — funcional, segurança, dados, política, COGS/PII.
4. **Localização** — `arquivo` + `line`.
5. **Mecanismo explicado** — não opinião.
6. **Não coberto** por linter/type-checker/CI já configurado.
7. **Ação concreta** — correção ou próximo passo quando aplicável.

**Escala de confiança:** 0 falso positivo · 25 hipótese fraca · 50 real com
evidência incompleta · 75 real e importante · 100 verificável e alto impacto.

- `lite` com ≤3 achados: auto-julgamento inline
- `standard`: um único juiz em lote — todos os candidatos de uma vez (`references/subagentes.md`)
- `deep`: juiz por achado

Atribua `confidence` 0–100 e `severity` (`critical` | `high` | `medium` | `low`).

**Done quando:** cada achado candidato tem confidence, severity e motivo.

### Passo 5 — Filtrar e classificar (inline, sem script)

| Confiança | Ação |
|-----------|------|
| ≥ 80 | **Publish** — vai para a review |
| 60–79 | **Hold** — métricas internas; não mostrar ao autor |
| < 60 | **Discard** |

Dedupe por `(file, line, category)` mantendo o de maior confidence.

Classificação 🔴/🟡/🟢: `references/entrega.md` §Classificação.

Só `publish` (≥80) na review. `hold` só em métricas internas.

### Modo bot vs modo completo

**Modo bot** (default ao postar) omite 🟢; **modo completo** inclui — ver
`references/entrega.md` §Modo bot vs completo. 🔴 e 🟡 ≥80 entram nos dois modos.

**Done quando:** lista publicada = só publish; classificação 🔴/🟡/🟢 aplicada.

### Passo 6 — Entregar

Formato, classificação e veredito: `references/entrega.md`. Ordem:

1. Contexto + tier (+ motivo se `deep`/`split`) + degradações (sem governança / sem ticket / cross-repo)
2. Raio de impacto (+ companion se cross-repo)
3. Achados: 🔴 → 🟡 → 🟢 (se completo)
4. Perguntas em aberto (intenção/produto **ou** companion não informado — não nits)
5. **Veredito** — `references/entrega.md` §Veredito
6. **Métricas** (publish/hold/discard) — sempre; tabela completa de custo
   (tier/specialists/tokens est.) só em **modo completo** (chat ou "review completo")

Se nada ≥80: *"Nenhum problema concreto de alta confiança foi identificado."*

Confirme com o usuário antes de postar:

```bash
gh pr comment <n> --repo <owner/repo> --body-file review.md
```

**Done quando:** entrega na ordem acima + veredito coerente com achados publicados.

## Só comente o que passa nos 7 critérios

Estilo isolado, nit, preexistente, “faltam testes” genérico e o que linter/CI já
cobre ficam de fora — viram silêncio ou hold, não comentário ao autor.

## Hotfix / `release/*`

Com governança, task hotfix/release urgente: `explicit_policy_violation` → 🟡/🟢
(dívida), nunca 🔴 — ver `references/entrega.md` §Anti-padrões e
`references/subagentes.md` (policy-reviewer). Sem governança: ignore.

## Scripts

| Script | Função |
|--------|--------|
| `scripts/triage.py` | Tier + especialistas + sinais |

## Referências

| Arquivo | Conteúdo |
|---------|----------|
| `references/checklists-core.md` | Checks genéricos + fluxo cross-repo |
| `references/subagentes.md` | Matriz sinais→especialistas + regras comuns + prompts |
| `references/entrega.md` | Classificação 🔴/🟡/🟢 + template PIA + veredito + métricas |
