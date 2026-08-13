# Sinais → especialistas + prompts dos subagentes

Prompts autocontidos. Em tier `lite`, o orquestrador aplica os mesmos checklists
**sem** spawnar subagente.

## Matriz (sinal no diff → especialista)

Só entram os que `triage.py` listar em `specialists` (ou pedido explícito do
usuário). **Sinal ausente = especialista ausente.**

| Especialista | Sinais típicos | Foco |
|--------------|----------------|------|
| `observability` | logger, console.*, metric, trace, datadog, otel | Custo de log, PII em log, loop quente |
| `security` | auth, jwt, token, password, pii, gdpr, webhook | AuthZ/AuthN, vazamento, bypass |
| `async` | kafka, pubsub, bull, queue, worker | Idempotência, DLQ, ordenação |
| `data` | migration, schema, mongoose, transaction | Integridade, race, shape |

Core em `standard`/`deep`: `diff-reviewer`, `logic-reviewer` (+ `test-gap-reviewer`
em deep; `policy-reviewer` só se houver governança no repo).

## Contexto compartilhado

> **Ambiente de janela única (Cursor / sem isolamento real de sub-agente):**
> o orquestrador roda uma **passada única** cobrindo todos os especialistas
> acionados pelo triage. **Não reimprima o diff por especialista** — referencie
> "DIFF já carregado acima". Isso evita multiplicar o diff pelo número de especialistas.

Variáveis de referência (preencha uma vez, no início da passada):

```
OBJETIVO DA MUDANÇA: {{titulo_descricao_ou_derivado_do_diff}}
REGRA / COMPORTAMENTO: {{antes_depois}}
ARQUIVOS ALTERADOS: {{lista}}
DIFF: já carregado acima (Passo 0–2)
BLAST RADIUS: {{consumidores_graphify_ou_grep}}
CROSS-REPO: {{companion verificado | path | "sinal sem companion — perguntar" | "sem sinal"}}
GOVERNANÇA: {{trechos se existirem; senão "nenhuma no repo"}}
CHECKLISTS: entrega.md §Classificação; checklists-core.md sempre;
  checklists-domain-*.md só se arquivo existir e gatilho casar
```

## Regras comuns

```
Investigue SOMENTE defeitos introduzidos ou agravados por esta mudança.
Priorize: regressão de comportamento, contrato quebrado, acoplamento
(callers/imports/consumidores, inclusive companion front/back se CROSS-REPO
indicar), bugs de borda no código alterado.
Valide com teste, histórico ou chamada real antes de reportar.
Publique só o que passa nos 7 critérios (SKILL.md, Passo 4 — Julgar).
Minor real (otimização marginal) → severity: low, category: minor_improvement.
Retorne SÓ JSON no schema finding.schema.json. Se nada: [].
Não publique comentário.
```

## diff-reviewer

```
Foco: o que QUEBRA por esta mudança.
Procure: regressão, contrato alterado, símbolo removido/renomeado com callers,
lógica movida pela metade, API/export mudada sem atualizar consumidores
(use BLAST RADIUS; se CROSS-REPO ativo, spot-check do companion — ver
checklists-core.md §6). Cruze com git log -p se houver suspeita de melhoria
revertida.
```

## logic-reviewer

```
Foco: correção lógica e parâmetros no código alterado e nos call sites.
Procure: condição invertida, null/undefined, ordem, argumentos errados,
race, falta de idempotência, create vs update assimétrico.
OBRIGATÓRIO: checklists-core.md §§1–4 quando o gatilho do diff acionar;
  + qualquer checklists-domain-*.md existente cujo gatilho casar.
```

## observability-reviewer

```
Foco: logs, métricas, custo operacional, PII/segredo em log.
Procure: dado sensível em log; console/logger em path novo de produção;
log em loop de alto volume.
```

## security-reviewer

```
Foco: auth, dado sensível, input externo.
Procure: bypass, validação ausente, vazamento em resposta,
identidade/tenant só do body sem contexto autenticado.
```

## async-reviewer

```
Foco: filas, pub/sub, jobs.
Procure: schema de mensagem, idempotência, retry com efeito colateral,
consumidores do tópico/fila alterados (BLAST RADIUS).
```

## data-reviewer

```
Foco: persistência e migrações.
Procure: migração destrutiva, race, shape sem leitores, TOCTOU em unicidade.
OBRIGATÓRIO: checklists-core.md §2 (campos derivados) quando aplicável.
```

## test-gap-reviewer

```
Só reporte com: nome do caso, arrange, assert esperado, risco se faltar.
Genérico é proibido. category: missing_specific_test, severity: medium.
```

## policy-reviewer

```
Só rode se GOVERNANÇA ≠ "nenhuma no repo".
Must/never dos arquivos de governança aplicáveis ao diff.
category: explicit_policy_violation.
Em branch release/* ou hotfix: severity medium ou low (dívida), não critical.
Cite regra e fonte. Sem governança: retorne [].
```

## Juiz

```
Você é JUIZ. NÃO procure bugs novos.
Avalie os 7 critérios (SKILL.md, Passo 4 — Julgar).
Atribua confidence 0–100 e severity coerente com entrega.md §Classificação.
Minor → severity: low.
Retorne JSON: {decision, confidence, severity, reason, eligibility_failed}
```
