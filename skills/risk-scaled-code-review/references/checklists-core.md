# Checklists core (genéricos)

Aplique **sempre** — em qualquer tier e qualquer repositório — quando o diff
tocar os padrões abaixo.

## 1. Consistência de normalização (create vs update)

**Quando:** o diff altera validação/persistência/comparação de um campo
(email, phone, documento, slug, código).

**Verificar:**

- Create normaliza o valor? (lowercase, trim, VO, parser)
- Update usa a **mesma** normalização antes de comparar e antes de query?
- Testes cobrem case/whitespace divergente?

**Falha típica:** create grava `foo@bar.com`, update aceita `FOO@BAR.COM` como
"diferente" e bypassa unicidade.

→ `logic_error`, severity `high`.

## 2. Cleanup de campos derivados

**Quando:** update condicional popula campo derivado (`*_id`, flags, hashes,
identificadores derivados de input).

**Verificar:**

- Se o campo pai é removido/null/empty, o derivado é anulado?
- Query de unicidade que inclui o derivado — órfão bloqueia erroneamente?

**Falha típica:** limpar o campo pai mas manter o derivado → falso positivo ou
identificador inconsistente.

→ `logic_error` ou `data_integrity`, severity `high` / `medium`.

## 3. Dependência opcional que silencia regra

**Quando:** unicidade/consulta/autorização depende de um contexto resolvido
(integração, tenant, feature flag, metadata).

**Verificar:**

- Util retorna early (`null`/`undefined`) se o contexto for falsy?
- Isso **silencia** a checagem em vez de falhar com 4xx explícito?
- Create e update tratam o fallback de forma **simétrica**?

→ `logic_error`, severity `high`.

## 4. Escopo da PR vs task

**Quando:** diff inclui auth, módulos adjacentes ou controllers além do fix.

**Verificar:**

- Mudanças colaterais têm teste ou justificativa na descrição?
- Branch de release/hotfix — risco de regressão cruzada entre módulos adjacentes?

→ `scope_too_large` ou achado 🟡 de processo; severity `medium`.

## 5. Test gap concreto (não genérico)

Para cada achado 🔴/🟡 de lógica acima, exija:

- Nome do `it()` / caso de teste sugerido
- Arrange mínimo (estado, payload, flags)
- Assert esperado (status, mensagem, campo persistido)

Sem isso → não publique `missing_specific_test`.

## 6. Contrato cross-repo (front ↔ back)

**Quando:** o diff altera rota, payload, schema, status, auth header/cookie,
enum, campo de formulário enviado à API, ou evento consumido/produzido pela
outra camada — ou triage `needs_cross_repo_check: true`.

**Fluxo (quando o sinal casar):**

1. Identifique o contrato tocado (rota, campo, schema, evento).
2. Companion (API ou client) desconhecido → **pergunte** o repo/path no chat
   antes de fechar a review (não invente o repo).
3. Spot-check do companion — só o contrato, não review completa; preferir o
   diff do PR irmão (mesmo ticket/branch) ao `main`/`default`.
4. Companion inacessível → degradar (`cross-repo não verificado`) e **não**
   inventar 🔴; o contrato vira pergunta em aberto.

**Verificar:**

- O companion espera o **mesmo** shape/nome/obrigatoriedade?
- Normalização (trim, case, VO) é simétrica entre quem envia e quem valida?
- Evidência cita os **dois** lados (arquivo:linha ou trecho de schema).

**Falha típica:** front passa a enviar campo novo/renomeado; backend ainda
lê o antigo (ou o contrário) → comportamento pela metade em produção.

→ `logic_error` / contrato quebrado, severity `high` (com evidência nos dois
lados) ou hold se companion indisponível.
