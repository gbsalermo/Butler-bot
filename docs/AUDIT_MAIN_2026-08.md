# Auditoria estrutural da `main` — agosto/2026

Objetivo: revisar inconsistências entre código, documentação e comportamento, sem promover uma refatoração arriscada no mesmo passo.

## Resumo

A `main` funciona como um sistema operacional acumulado por camadas. O maior risco não é um bug isolado: é **uma pessoa nova editar uma camada preservada/legada achando que ela é a fonte de verdade da produção**.

### Classificação

- **Crítico:** CI descrito como proteção automática não conseguia importar parte do Worker em CPython.
- **Alto:** README/CONTINUIDADE descreviam `context_router`, `intent_parser`, sugestões e Library como fluxo oficial, mas o dispatcher atual não os usa como camada central.
- **Alto:** coexistem `cloudflare/src/` (produção) e `src/` (polling/SQLite legado) dentro da mesma branch sem aviso forte no diretório legado.
- **Médio:** política final depende da ordem de vários monkeypatches em `entry.py`.
- **Médio:** documentação do Worker estava desatualizada em horários, migrations e identificador do dispatcher.
- **Médio:** `runtime_schema.py` era descrito como proteção ativa, mas não é chamado pelo dispatcher atual.
- **Médio:** há mais de uma definição de menus e políticas de lembrete; algumas são deliberadamente sobrescritas depois.
- **Médio:** política documentada para frases de falta doméstica divergia do comportamento real.
- **Baixo/Médio:** `TIMEZONE_NAME` existe, mas o runtime usa offset fixo; o nome pode induzir manutenção errada.
- **Dívida técnica:** dados/configuração pessoal do proprietário ainda estão versionados no código.

## 1. CI CPython × runtime Pyodide

### Problema

`cloudflare/src/telegram_api.py` importa `js` e `pyodide.ffi`, fornecidos pelo runtime Cloudflare. A suíte roda no GitHub Actions usando CPython comum.

Testes que importam `app.py` transitivamente falhavam na coleta com `ModuleNotFoundError: js`.

### Correção nesta branch

Adicionar `cloudflare/tests/conftest.py` com stubs mínimos **somente para import** em testes determinísticos.

O stub falha se um teste tentar realizar `fetch` real, evitando falsa integração.

## 2. Arquitetura documentada não era a arquitetura ativa

### Documentação antiga

README e continuidade colocavam:

```text
Context Router + Intent Parser
→ Core
→ memória
→ sugestões
→ Library
→ conversa
```

### Produção real

`entry.py` usa uma cadeia explícita de handlers e fast paths. `context_router.py` e `intent_parser.py` aparecem principalmente em testes/código preservado, não como dispatcher central.

O `/health` também declara explicitamente:

- broad NLU desabilitada;
- Library genérica desabilitada;
- sugestões transversais genéricas desabilitadas;
- memória pessoal genérica desabilitada.

### Ação

`docs/ARCHITECTURE.md` passa a ser a fonte de verdade operacional.

## 3. Testes que não necessariamente protegem produção

`test_context_router.py` é útil para preservar a arquitetura experimental, mas não prova que `entry.py` roteará a mensagem da mesma forma.

A suíte precisa distinguir:

- testes de módulos preservados;
- testes de fast paths ativos;
- testes do contrato do dispatcher final.

Recomendação futura: criar testes de integração leve do dispatcher com DB/Telegram fakes.

## 4. Runtime duplicado

### Produção

`cloudflare/` — Webhook + Worker + D1.

### Legado

`src/` — polling + `python-telegram-bot` + SQLite.

Risco: corrigir `src/natural_handlers.py` e esperar mudança no bot em produção.

### Ação

Adicionar `src/README.md`, reforçar no README raiz e no guia de manutenção.

## 5. Monkeypatches dependentes de ordem

Exemplos encontrados:

- `performance_patch` substitui `app.ensure_user`;
- `quality_patch` altera política de checkpoint e item scheduler;
- `reminder_policy` desliga a política de item instalada anteriormente;
- `scheduled_delivery_guard` troca canais de envio por wrappers com confirmação;
- `operational_menu` altera menus e instala metas;
- `production_usability_patch` altera menus-base e adiciona Ler/Ver Depois.

Isso funciona, mas a ordem em `entry.py` é um contrato implícito.

### Ação

Documentar a ordem e proibir novos patches sem registrar símbolo substituído e predecessor.

### Recomendação futura

Consolidar patches progressivamente dentro do módulo autoritativo quando houver cobertura suficiente.

## 6. Menus com múltiplas fontes

Existem definições em:

- `app.py`;
- `operational_menu.py`;
- `quality_patch.py`;
- `production_usability_patch.py`;
- `conversation_layer.py`;
- `runtime_guard.py`.

Nem todas representam o menu final; algumas são fallback/teclas locais.

Risco: botão aparecer em um caminho de volta e não em outro.

### Ação

Documentar `operational_menu.py` como autoridade visual principal e registrar que `app.*_KB` deve ser mantido coerente para fallbacks.

## 7. Lembretes: código antigo ainda existe

Há implementações antigas de política temporal em módulos como `quality_patch` e scheduler legado, mas `reliable_reminders.py` é a autoridade atual.

`reminder_policy.py` instala um `noop` para impedir duplicidade no scheduler antigo.

`scheduled_delivery_guard.py` também injeta confirmação real de entrega.

### Ação

Documentar explicitamente essa cadeia. Não remover código legado no mesmo PR de documentação sem teste de integração.

## 8. Documentação de horários desatualizada

Foram encontradas divergências:

- documentação dizia resumo matinal em 07:30, configuração atual usa 07:00;
- documentação dizia compromisso 10 minutos antes, política atual usa 5 minutos;
- `/health` declarava dispatcher diferente do descrito no README do Worker.

### Ação

Atualizar `cloudflare/README.md` para refletir constantes e `/health` atuais.

## 9. Migrations incompletas na documentação

`cloudflare/README.md` citava principalmente `0001` e `0002`, mas já existem:

- `0003_attendance.sql`;
- `0004_conversation_context.sql`;
- `0005_goal_profiles.sql`.

### Ação

Documentar todas e deixar claro que módulos podem ter `ensure_schema()` defensivo.

## 10. `runtime_schema.py` não é bootstrap automático

O arquivo possui `ensure_runtime_schema`, mas não há import/execução no dispatcher atual.

Também existe uma função homônima `ensure_runtime_schema` em `runtime_guard.py` que hoje é deliberadamente `noop`.

### Risco

Uma pessoa pode adicionar tabela ao helper e acreditar que ela será criada em produção.

### Ação

Documentar migrations como fonte formal e marcar helper como compatibilidade/manual.

## 11. Política de mercado divergia da documentação

README/continuidade descreviam `acabou o café` como problema que deveria gerar sugestão/confirmar antes de escrita.

O código de produção atual em `grocery_phrase_patch.py` interpreta formas claras como `acabou`, `falta`, `tô sem` como atualização explícita do estado doméstico e grava diretamente na lista.

Além disso, `quality_patch.py` possui fallback semelhante.

### Ação nesta auditoria

Documentar o comportamento **que realmente está em produção**, sem mudar política silenciosamente.

Se a política desejada voltar a ser “sugerir e confirmar”, isso deve ser uma decisão funcional separada com testes.

## 12. Library e sugestões preservadas, mas não ativas genericamente

Módulos existem e são úteis como base futura, porém buscas mostraram que vários não são importados pelo dispatcher atual:

- `context_router.py`;
- `intent_parser.py`;
- `action_policy.py`;
- `suggestion_engine.py`;
- `library_catalog_handler.py`;
- `context_memory.py`;
- parte da família `companion_*`, `cultural_*`, `general_memory.py` e `knowledge/`.

### Ação

Marcar esses módulos como **preservados/experimentais** no mapa de módulos e em `docs/BUTLER_LIBRARY.md`.

## 13. Configuração de timezone

`settings.py` define nome de timezone e offset UTC, mas o runtime constrói `timezone(timedelta(hours=UTC_OFFSET_HOURS))`.

`TIMEZONE_NAME` não é consumido atualmente.

### Ação

Documentar que o offset é a autoridade atual.

### Recomendação futura

Se o runtime suportar `zoneinfo`, usar uma única fonte de timezone e remover duplicidade.

## 14. Bootstrap otimizado e defaults futuros

`performance_patch.fast_ensure_user()` pula o bootstrap completo para usuários já conhecidos.

Isso melhora performance, mas significa que adicionar um novo default em `app.ensure_user()` **não atualiza automaticamente usuários existentes**.

### Regra de manutenção

Novos defaults para contas já existentes precisam de migration/backfill explícito.

## 15. Dados pessoais/configuração versionados

O perfil especial do proprietário e dados iniciais ainda residem em `settings.py`/`owner_profile.py`.

Isso não é bug para um bot pessoal, mas reduz reutilização e aumenta exposição de configuração pessoal em repositório público.

### Recomendação

Antes de transformar o Butler em produto reutilizável, mover identificação/configuração pessoal para secrets/config e seed privado.

## 16. Webhook secret opcional

`entry.py` valida `TELEGRAM_WEBHOOK_SECRET` quando existe, porém `wrangler.jsonc` exige apenas o token do Telegram.

### Estado

Não alterado nesta auditoria para não quebrar o deploy atual.

### Recomendação

Tornar o secret obrigatório em uma mudança de segurança separada, configurando produção antes de mudar para fail-closed.

## 17. Resultado esperado desta branch

- documentação operacional coerente;
- mapa de módulos;
- aviso claro sobre runtime legado;
- CI determinístico executável em CPython;
- regras de comentário/manutenção explícitas;
- nenhuma refatoração grande ou alteração silenciosa de política de negócio.

A próxima etapa recomendada depois do merge é uma refatoração incremental dos patches, começando por menus e política de reminders, sempre protegida por testes de integração do dispatcher.
