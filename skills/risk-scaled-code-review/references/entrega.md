# Classificação, formato e veredito

---

## Classificação de achados

A classificação combina **severidade técnica**, **confiança** (≥80 para publicar)
e **impacto de negócio/acoplamento**. Minor (`low`) **sempre** vira 🟢 Sugestão.

### Mapa severidade → entrega

| `severity` (schema) | Emoji | Nome | Bloqueia merge? |
|---------------------|-------|------|-----------------|
| `critical` | 🔴 | Crítico | Sim |
| `high` | 🔴 | Crítico | Sim |
| `medium` | 🟡 | Bloqueante | Precisa resposta ou correção consciente |
| `low` | 🟢 | Sugestão (minor) | **Não** |

**Regra minor:** se o achado for estético, otimização, dívida consciente documentada,
latência marginal ou nit com benefício concreto → `severity: low` → 🟢.
Nunca classifique bug de produção ou regressão de regra de negócio como `low`.

### Categorias (alto sinal)

| category | Quando | Severidade típica |
|----------|--------|-------------------|
| `compile_or_runtime_failure` | Não compila/roda; import quebrado | critical |
| `behavior_regression` | Quebra comportamento/contrato | critical / high |
| `logic_error` | Resultado errado; borda/ordem/parâmetro | critical / high |
| `security_vulnerability` | Auth, injeção, PII/segredo exposto | critical / high |
| `data_integrity` | Race, perda de dados, shape inconsistente | high / medium |
| `explicit_policy_violation` | Viola AGENTS/constitution/ADR | medium (🟡); low em hotfix release |
| `missing_specific_test` | Caso concreto faltando com risco demonstrável | medium |
| `scope_too_large` | Alerta único de `split` | medium |
| `minor_improvement` | Otimização, legibilidade, dívida consciente | **low → 🟢** |

### Critérios por emoji

**🔴 Crítico** — merge não deve acontecer sem resolver (confiança ≥80):
- Bug real em caminho que ocorre em produção
- Regressão da regra de negócio da task
- Quebra de contrato para consumidor mapeado no blast radius
- Falha de segurança ou integridade de dados imediata

**🟡 Bloqueante** — precisa resposta do autor antes de aprovar:
- Violação explícita de governança quando o repo tem AGENTS/constitution/ADR (fora de hotfix)
- Teste ausente para a regra específica que motivou a PR
- Acoplamento sensível / contrato quebrado para consumidor mapeado
- Escopo ampliado além da task com risco de regressão documentado
- Incerteza de produto que muda a correção (vira pergunta em aberto se conf <80)

**🟢 Sugestão (minor)** — não impede merge:
- Nomenclatura, bloco redundante, dupla chamada evitável
- Índice/performance sem evidência de problema atual (conf 60–79 → hold, não 🟢)
- Refactor futuro, documentação de dívida
- Policy em hotfix release registrada como dívida consciente

### Perguntas de decisão

1. Isso quebra algo para consumidor mapeado? → 🔴
2. Isso contraria regra escrita e não é hotfix urgente? → 🟡
3. Isso é melhoria marginal ou estilo com benefício concreto? → 🟢
4. Impacto incerto? → hold 60–79 ou pergunta aberta

### Anti-padrões

- 🔴 com confiança <80 → hold, não publique
- 🟡 genérico "faltam testes" sem caso → descarte
- 🟢 disfarçando bug → reprove no juiz (subir severity)
- Policy violation 🔴 em hotfix (quando há governança) → rebaixar para 🟡/🟢 com dívida

---

## Formato de comentário — PIA

Padrão: **PIA** (Problema → Impacto → Ação), em português.

| Bloco | Papel |
|-------|-------|
| **Problema** | O que está errado ou em risco (factual, 1–3 frases) |
| **Impacto** | Consequência concreta (negócio, consumidor, dado, segurança) |
| **Ação** | Correção proposta ou pergunta ao autor |

### Template por achado

```
[🔴|🟡|🟢] <título curto> — <arquivo>:<linha>

**Problema:** <descrição objetiva, 1–3 frases>

**Impacto:** <ligação com comportamento, consumidor do blast radius,
política do repo ou risco em produção — nunca genérico>

**Ação:** <ajuste concreto, teste a adicionar, ou pergunta ao autor>
```

**Tom:**
- Colaborativo: *"vale considerar…"*, *"podemos confirmar se…?"*
- Direto sobre risco em 🔴/🟡 — colaborativo ≠ suavizar bug real
- Não mencione IA, modelo ou ferramenta no corpo

### Exemplos

#### 🔴 Crítico

```
🔴 Update não aplica a mesma normalização do create — src/services/UserService.js:214

**Problema:** No create, o e-mail passa por `normalizeEmail()`; no update, a
query de unicidade usa `payload.email` cru.

**Impacto:** `FOO@BAR.COM` é tratado como valor novo — unicidade inconsistente
e possível duplicata lógica em produção.

**Ação:** Reusar `normalizeEmail()` no update antes da query; cobrir com teste
de casing.
```

#### 🟡 Bloqueante

```
🟡 Falta teste do caso de casing no update — test/UserService.update.spec.js

**Problema:** A suite cobre happy path de update, mas não o caso que motivou o fix.

**Impacto:** Regressão silenciosa se a normalização for removida depois.

**Ação:** Arrange com registro `foo@bar.com` e payload `FOO@BAR.COM`; assert
do status de conflito do contrato atual.
```

#### 🟢 Sugestão (minor)

```
🟢 Dupla resolução da mesma flag no mesmo request — src/handlers/create.js

**Problema:** A feature flag é lida no handler e de novo no service no mesmo fluxo.

**Impacto:** Latência marginal; sem risco funcional imediato.

**Ação:** Passar o valor já resolvido ao service, se quiser evitar a segunda chamada.
```

### Ordem da review completa (chat ou PR)

1. **Metadados** — PR/branch, tier, degradações (sem governança / grep / sem ticket / cross-repo)
2. **Contexto** — regra/comportamento alterado, antes/depois
3. **Raio de impacto** — consumidores/superfícies (fonte: grep; + companion se houver)
4. **Achados** — 🔴 → 🟡 → 🟢 (🟢 só se completo)
5. **Pontos positivos** — opcional (2–4 bullets)
6. **Perguntas em aberto** — produto/intenção **ou** companion não informado
7. **Veredito** — §Veredito abaixo

Se vazio após filtro: *"Nenhum problema concreto de alta confiança foi identificado."*

| Onde | Formato |
|------|---------|
| Inline no arquivo | Só template PIA + emoji |
| Summary no PR | Review completa |
| Chat | Review completa + métricas internas |

---

## Modo bot vs modo completo

| Modo | Quando | 🟢 |
|------|--------|-----|
| **Bot** (default ao postar) | “posta no PR” | Omitir |
| **Completo** | “review completo” / “incluir sugestões” | Incluir |

🔴 e 🟡 ≥80 entram nos dois modos.

---

## Veredito da review

O veredito **deriva da contagem de achados publicados**, não da "direção correta"
da solução. Uma PR pode ir na direção certa e ainda exigir alterações.

### Matriz de decisão

| Condição | Veredito | Recomendação |
|----------|----------|--------------|
| Tier `split` | **Não revisar** | Pedir quebra do PR |
| ≥1 🔴 com confiança ≥85 | **Solicitar alterações** | Request changes |
| ≥2 🔴 (qualquer conf ≥80) | **Solicitar alterações** | Request changes |
| 1 🔴 + ≥2 🟡 | **Solicitar alterações** | Request changes |
| Apenas 🟡 (sem 🔴) | **Aprovar com ressalvas** | Approve with suggestions |
| Apenas 🟢 ou vazio | **Aprovar** | Approve |
| 🔴 apenas em hold (60–79) | **Aprovar com ressalvas** | Mencionar incertezas nas perguntas abertas |

### Template de saída

```
| Critério | Avaliação |
|----------|-----------|
| Direção da solução | ✅ / ⚠️ / ❌ |
| Testes | ✅ / ⚠️ / ❌ |
| Risco de merge | Baixo / Médio / Alto |
| Achados publicados | 🔴 n · 🟡 n · 🟢 n |
| **Recomendação** | **<veredito>** |
```

**Como preencher "Direção da solução":**
- ✅ — abordagem alinha com a regra de negócio da task
- ⚠️ — direção ok, execução com gaps nos achados
- ❌ — abordagem contradiz requisito (raro; explicar no 🔴)

**Importante:** direção ✅ **não** upgrade veredito de "Solicitar alterações" para "Aprovar".

### Exemplos de veredito

| Achados | Veredito |
|---------|----------|
| 2 🔴 + 3 🟡 | Solicitar alterações |
| 0 🔴 + 2 🟡 + 5 🟢 | Aprovar com ressalvas (🟢 omitidos no bot) |
| 0 🔴 + 0 🟡 | Aprovar |
| 5 🔴 | Solicitar alterações (mesmo com testes "bons no happy path") |

### Perguntas em aberto vs veredito

- Perguntas **não substituem** 🔴 — se o risco é claro, classifique e solicite alterações.
- Perguntas servem quando confiança 60–79 ou decisão de produto muda a correção.

---

## Métricas (interno — modo completo)

Registre no chat (não no comentário ao autor):

| Campo | Exemplo |
|-------|---------|
| tier | deep |
| specialists | data, security |
| arquivos / linhas | 8 / 867 |
| publish / hold / discard | 6 / 2 / 3 |
| tool calls (est.) | ~25 |
| tokens entrada / saída (est.) | ~55k / ~18k |

**Hold (60–79):** inclua a contagem no relatório ao usuário que rodou a skill,
não no comentário ao autor do PR. Serve calibração do threshold.

**Calibração:** verdadeiro positivo = autor alterou código em resposta no mesmo
PR. Meta precision ≥70% (senão suba threshold para 85); recall amostral ≥40% em
~30 PRs (precision >80% e recall baixo → baixe para 75). Se `lite` raro demais
ou especialistas disparando >50% sem achados → revise limiares em `triage.py`.
