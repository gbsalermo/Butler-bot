# Butler Bot — Cloudflare Worker

Este diretório contém o **runtime de produção** do Butler: Telegram Webhook + Cloudflare Python Worker + D1 + Durable Objects.

## Antes de editar código

Leia nesta ordem:

1. `../docs/STATUS_ATUAL.md` — fase/subetapa atual e próximo trabalho;
2. `../docs/BUTLER_DOSSIE_MESTRE.md` — visão completa do produto;
3. `../docs/ARCHITECTURE.md` — fonte de verdade do runtime;
4. `../docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` — roadmap oficial;
5. `../docs/ETAPA_1_4_CORRECOES.md` — trabalho funcional aberto no snapshot de 31/08/2026;
6. `../docs/SCHEDULER_REDUNDANCY.md` — contingência temporal via Durable Objects;
7. `../docs/MAINTAINER_GUIDE.md` — regras práticas;
8. `src/README.md` — mapa módulo por módulo.

`../docs/AUDIT_MAIN_2026-08.md` e `../docs/INVENTARIO_ETAPA_0.md` são históricos da Etapa 0.

---

## Estrutura de produção

```text
wrangler.jsonc
  main = src/worker.py

src/worker.py
  → mantém AttendanceAlarm / PersonalAlarm
  → rearma Durable Objects fora do caminho crítico do webhook
  → sincroniza alarms no cron
  → herda src/entry.py

src/entry.py
  → GET /health
  → POST /telegram/webhook
  → dispatch_callback()
  → dispatch_message()
  → dispatch_scheduled()

src/app.py
  → núcleo-base/fallback, D1, estados e operações herdadas
```

Branch de produção: `main`.

A ordem de handlers e de instalações em `entry.py` é parte do comportamento.

---

## Estado funcional atual

A Etapa 0 foi concluída. A Etapa 1 está em andamento:

```text
1.1 auditoria da linguagem           ✅
1.2 base linguística comum           ✅
1.3 contexto curto/referências       ✅
1.4 correção/auto-reparo             🚧
```

A primeira fatia da 1.4 já foi mesclada e corrige tempo do item recém-criado sem duplicação.

Consulte `../docs/STATUS_ATUAL.md` antes de começar qualquer nova frente.

---

## Dispatcher operacional

Resumo atual da precedência:

```text
/start/reset
→ aviso administrativo / diagnósticos
→ despedida prioritária
→ usabilidade / Ler-Ver Depois
→ menu / rotinas / presença UI / navegação
→ core_fast_path
→ presença / provas / acadêmico
→ correction_patch
→ lembrete explícito
→ referência curta
→ tarefa / runtime_guard
→ mercado / quality / treino / conversation_layer
→ app.py somente quando botão/estado guiado exigir
→ fallback
```

Callbacks:

```text
admin announcement
→ attendance
→ context/item
```

O antigo desenho `context_router.py + intent_parser.py` continua preservado, mas não governa o webhook principal.

---

## Linguagem natural ativa

A arquitetura da Etapa 1 é conservadora:

```text
language_primitives.py
→ famílias linguísticas / polaridade
→ sem D1, Telegram ou CRUD

short_context.py
→ contexto curto expirável e isolado por usuário

reference_patch.py
→ referências recentes/posicionais

correction_patch.py
→ auto-reparo seguro do item recém-criado
```

Broad NLU, Library genérica, sugestões transversais e memória pessoal genérica continuam desabilitadas.

---

## Funcionalidades operacionais

### Interface e identidade

- `/start`;
- menu principal e Cotidiano;
- identificação por `telegram_chat_id`;
- isolamento por `user_id`;
- perfil especial do proprietário por `is_owner(chat_id)`;
- usuário genérico sem grade/protocolo pessoal automático.

### Day-off

Day-off vale para o dia local em que foi ativado e não é automático em sábado/domingo. A expiração acontece antes do restante do cron e também é protegida no fluxo de alarms.

### Tarefas, compromissos e lembretes

- criação por botão e linguagem natural conservadora;
- conclusão, cancelamento e adiamento;
- agenda de hoje/amanhã/períodos;
- pendências;
- referências curtas;
- correção temporal do item recém-criado;
- entrega temporal por `reliable_reminders.py`.

### Acadêmico e presença

- matérias, horários e locais;
- importação textual/PDF pesquisável, sem OCR;
- provas e lembretes;
- faltas/presença e limites;
- alertas de aula;
- Durable Object específico para presença.

### Mercado

- adicionar/listar itens faltando;
- marcar compra concluída;
- formas claras como `acabou café`/`tô sem detergente` atualizam diretamente a lista segundo a política atual.

### Rotinas e metas

- recorrência e múltiplos checkpoints;
- integração com agenda;
- conclusão pode alimentar meta;
- edição/remoção.

### Musculação

- protocolo pessoal preservado;
- perfil genérico com treino próprio;
- exercício, substituição, séries, cargas, repetições e progresso.

### Ler/Ver Depois

Categorias visíveis atuais:

```text
📚 Livros
🎬 Filmes
🎓 Cursos
🗂️ Outras
```

A categoria `Cursos` não significa que o domínio completo de Cursos/Trilhas da Etapa 4 esteja pronto.

### Clima

- Open-Meteo;
- localização por usuário;
- agenda Hoje/Amanhã + previsão;
- resumo matinal;
- `weather_personality.py` para comentário mais humano sem alterar dados objetivos;
- fallback seguro se a API falhar.

### Administração

Somente proprietário:

- status/listagem de usuários;
- `/aviso` com prévia;
- confirmação/cancelamento por botão;
- envio geral ou direcionado;
- estado pendente idempotente no D1.

---

## Scheduler e redundância

O Cron Trigger configurado em `wrangler.jsonc` roda a cada minuto e continua a linha primária:

```text
day_off
→ attendance
→ daily_items / reliable_reminders
→ routines
→ reliable_summaries
→ app.scheduled_tick (compatibilidade/legado)
```

Após o incidente de 30/08/2026, existe também uma linha persistente de contingência:

```text
webhook/cron
→ sync_personal_alarms()
→ PersonalAlarm por usuário
→ próximo evento persistido
→ alarm()
→ dispatchers autoritativos
```

`PersonalAlarm` cobre tarefa com horário, compromisso, lembrete simples, checkpoint de rotina, resumo matinal e fechamento semanal. `AttendanceAlarm` continua separado.

Após webhook, o rearme usa `ctx.waitUntil(...)`, fora do tempo de resposta. No cron, a sincronização permanece síncrona.

`reliable_reminders.py` continua sendo a autoridade única de `daily_items`, e `notification_log` protege a idempotência entre Cron e Durable Objects.

`reminder_policy.py` foi removido na Etapa 0.

Detalhes: `../docs/SCHEDULER_REDUNDANCY.md`.

---

## Desempenho

`performance_patch.py` reduz round-trips D1 no caminho quente com cache local ao update para:

```text
telegram_chat_id → user_id
user_sessions
```

Esse cache não persiste entre updates.

Também foram adotados:

- gates lexicais antes de consultas de contexto;
- remoção de DDL de presença do dispatcher geral;
- reconciliação de alarms fora da resposta interativa.

---

## D1 e migrations

A evolução formal do banco está em `migrations/`:

```text
0001_initial.sql
0002_app_state.sql
0003_attendance.sql
0004_conversation_context.sql
0005_goal_profiles.sql
0006_weather_preferences.sql
0007_admin_pending_announcements.sql
0008_later_items.sql
```

As subetapas 1.1–1.4 reutilizam estruturas existentes e não adicionaram migration até o snapshot atual.

Alguns módulos executam `CREATE TABLE/INDEX IF NOT EXISTS` defensivamente para implantação incremental. Isso não substitui migration.

### Aplicar migrations

Produção/remoto, somente depois de validação:

```bash
npx wrangler d1 migrations apply butler-db --remote
```

Local:

```bash
npx wrangler d1 migrations apply butler-db --local
```

Migration destrutiva exige snapshot/export e plano de rollback.

---

## `/health`

```text
GET /health
```

O manifesto operacional identifica o dispatcher e expõe capacidades/flags. Ao alterar comportamento material, confirme que as flags continuam verdadeiras.

Não trate `/health` como substituto de teste de fluxo real.

---

## Arquitetura preservada

`src/knowledge/` e módulos de Library/contexto/memória continuam preservados para etapas futuras.

Não implementar correção de produção apenas em `context_router.py`, `intent_parser.py`, `suggestion_engine.py`, `library_catalog_handler.py` etc. sem primeiro conectar/testar o caminho real no dispatcher.

A raiz `../src/` também permanece como runtime histórico polling/SQLite.

---

## Testes

```bash
pytest -q
```

GitHub Actions executa compilação e regressão determinística. A suíte CPython usa stubs mínimos de `js`, `pyodide` e `workers`; não simula integração real de rede.

Há regressões específicas para:

- ordem de callbacks/dispatcher/cron;
- linguagem da Etapa 1;
- contexto curto e referências;
- auto-reparo temporal;
- fallback persistente do scheduler;
- caminho quente/round-trips D1;
- personalidade da previsão.

CI verde não prova deploy Cloudflare.

---

## Desenvolvimento local e segurança

Ao testar Telegram, use bot separado e túnel/webhook temporário. Não substitua o token oficial só para validar branch.

- `TELEGRAM_BOT_TOKEN` permanece secret;
- webhook aceita `TELEGRAM_WEBHOOK_SECRET` quando configurado;
- queries pessoais devem limitar por usuário;
- tokens não entram em logs/repositório;
- callbacks administrativos revalidam autorização/estado no servidor.

---

## Regra para expansão

Antes de criar outro módulo/patch, responda:

1. `docs/STATUS_ATUAL.md` permite começar essa frente agora?
2. qual módulo já é dono desse domínio?
3. por que a mudança não cabe nele?
4. quem importa/chama o novo código?
5. qual posição precisa no dispatcher?
6. qual símbolo será sobrescrito?
7. como a camada será removida depois?
8. qual teste demonstra o comportamento final de produção?

O objetivo é crescer em capacidade sem voltar a crescer em desordem arquitetural.
