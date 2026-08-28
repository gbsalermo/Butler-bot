# Arquitetura do Butler — fonte de verdade de produção

> Este documento descreve **o que a `main` realmente executa hoje**. Ele tem prioridade sobre descrições históricas em `CONTINUIDADE.md` e sobre módulos preservados que não estão ligados ao dispatcher.

## 1. Regra de ouro

A produção atual é o código em `cloudflare/`.

```text
Telegram
  ↓ webhook
cloudflare/src/worker.py
  ↓
cloudflare/src/entry.py
  ↓
handlers operacionais + D1
```

O diretório `src/` na raiz é o runtime antigo de polling/SQLite. Ele permanece como referência/fallback e **não é a implementação implantada pelo Cloudflare Worker**.

Antes de alterar qualquer comportamento, confirme em qual runtime a alteração pertence.

## 2. Entrypoints

### `cloudflare/src/worker.py`

É o entrypoint configurado em `wrangler.jsonc`.

Responsabilidades:

- herdar o dispatcher HTTP de `entry.Default`;
- sincronizar Durable Objects de alarmes de presença;
- sincronizar Durable Objects de alarmes pessoais;
- delegar o restante do cron para `entry.Default.scheduled()`.

### `cloudflare/src/entry.py`

É o dispatcher de produção. Ele define:

- `GET /health`;
- `POST /telegram/webhook`;
- ordem de instalação dos patches;
- prioridade dos handlers de mensagem;
- ordem dos subsistemas do cron.

**A ordem neste arquivo é parte do comportamento.** Mover imports, `install_*()` ou handlers sem entender quem sobrescreve quem pode criar regressões silenciosas.

### `cloudflare/src/app.py`

É o núcleo-base herdado da primeira versão do Worker. Contém:

- acesso a D1;
- bootstrap de usuários;
- estados guiados;
- menus-base;
- agenda, tarefas, mercado, finanças, metas e treino;
- scheduler legado.

Importante: várias funções e constantes de `app.py` são substituídas em runtime por módulos `*_patch.py`, `*_fix.py`, `*_integration.py` e `operational_menu.py`. Portanto, **não assuma que uma constante em `app.py` representa a interface final de produção**.

## 3. Dispatcher real de mensagens

A ordem atual em `entry.py` é, resumidamente:

```text
1. /start e reset
2. diagnósticos de alertas
3. despedidas prioritárias
4. usabilidade/lista Ler-Ver Depois
5. menus/rotinas/presença/navegação global
6. core_fast_path
7. presença + provas + acadêmico
8. lembrete explícito / referências / tarefas / runtime_guard
9. mercado informal / quality / treino / conversation_layer
10. app.handle_message apenas para botão, /start ou estado guiado ativo
11. fallback "não entendi"
```

`core_fast_path.py` também chama `weather_context.py` antes dos botões exatos de Hoje/Amanhã. Isso permite anexar clima à agenda sem gerar duas respostas para o mesmo pedido.

Um handler retorna `True` quando consumiu a mensagem. Depois disso os handlers seguintes não rodam.

### Consequência para manutenção

Quando uma frase é tratada no módulo “errado”, não basta procurar um regex. É preciso verificar **qual handler anterior a interceptou**.

## 4. Instalação de patches

`entry.py` executa instalações no import. A sequência atual é intencional:

```text
performance_patch
scheduler_patch
routine_integration
routine_ui_patch
conversation_layer
quality_patch
natural_behavior recurrence patch
academic_intelligence
academic_polish
exam_cancel_patch
personality_variants
reminder_policy
ux_bugfixes
task_context_patch
attendance_patch
attendance_enhancement
attendance_management
attendance_production_fix
task_emoji_patch
workout_progress_patch
scheduled_delivery_guard
operational_menu
production_usability_patch
```

### Patches que se sobrescrevem deliberadamente

- `quality_patch` instala uma política antiga de lembretes em `conversation_layer`;
- `reminder_policy` substitui essa política por `noop`, porque `reliable_reminders.py` passou a ser a autoridade;
- `scheduled_delivery_guard` troca os canais de envio de schedulers por uma versão que exige confirmação real do Telegram;
- `operational_menu` redefine menus e instala a família de metas;
- `production_usability_patch` ainda ajusta menus-base de `app` e adiciona Ler/Ver Depois.

Essas relações precisam permanecer documentadas. Se um patch novo sobrescrever o mesmo símbolo, registrar aqui.

## 5. Autoridade por domínio

| Domínio | Fonte principal atual | Observação |
|---|---|---|
| Menu principal/Cotidiano | `operational_menu.py` | `app.py` contém fallback/base |
| Tarefas | `task_context_patch.py`, `runtime_guard.py`, `app.py` | fast paths podem criar antes do fluxo guiado |
| Lembretes simples | `colloquial_reminder_fastpath.py`, `natural_behavior_patch.py`, `reliable_reminders.py` | aviso de tarefa no horário; compromisso 5 min antes |
| Compromissos | `operational_menu.py`, `app.py`, `reliable_reminders.py` | lista operacional filtra resolvidos antigos |
| Mercado | `grocery_phrase_patch.py`, `core_actions.py`, `app.py` | relatos claros de falta atualmente gravam direto |
| Acadêmico | `academic_intelligence.py` + família `attendance_*` + `exam_*` | presença possui scheduler próprio |
| Rotinas | `routine_integration.py`, `runtime_guard.py`, `routine_editing.py` | `conversation_layer.py` complementa agenda/contexto |
| Metas | `goal_operational.py` + `goal_*` | instalados por `operational_menu.install()` |
| Musculação | `workout_progress_patch.py`, `app.py`, `protocol_mass_data.py` | perfil proprietário e perfil genérico divergem |
| Ler/Ver Depois | `production_usability_patch.py` | schema criado de forma idempotente pelo próprio módulo |
| Clima | `weather_context.py`, `weather_service.py` | Open-Meteo; Hoje/Amanhã + configuração por usuário + resumo matinal |
| Resumos | `reliable_summaries.py` | manhã 07:00, agora com clima quando habilitado; semanal domingo 20:00 |
| Alarmes persistentes | `attendance_alarm.py`, `personal_alarm.py` | Durable Objects sincronizados por `worker.py` |

## 6. Scheduler real

O cron do Worker roda a cada minuto.

`worker.py` primeiro sincroniza alarmes persistentes. Depois `entry.Default.scheduled()` executa, isoladamente:

```text
attendance
→ daily_items / reliable_reminders
→ routines
→ summaries
→ app.scheduled_tick (legado/compatibilidade)
```

`scheduler_runtime.run_isolated()` impede que a falha de um subsistema cancele os seguintes.

### Política de lembretes atual

- aula: T-10 e evento de início, conforme módulo de presença;
- tarefa com horário: no horário configurado;
- compromisso: 5 minutos antes;
- lembrete pessoal simples: no horário, com janela curta para evitar aviso obsoleto;
- resumo da manhã: 07:00, incluindo previsão do tempo quando disponível/habilitada;
- fechamento semanal: domingo 20:00.

A falha da API meteorológica não deve derrubar o resumo: `weather_service.safe_forecast_text()` degrada silenciosamente para agenda sem clima e registra diagnóstico.

`notification_log` é usado para idempotência.

## 7. Banco e schema

### Fonte formal

As migrations em `cloudflare/migrations/` são o registro formal de evolução do D1:

- `0001_initial.sql` — schema-base;
- `0002_app_state.sql` — sessão/estado e treino incremental;
- `0003_attendance.sql` — presença;
- `0004_conversation_context.sql` — contexto experimental da arquitetura anterior;
- `0005_goal_profiles.sql` — perfis/configuração de metas;
- `0006_weather_preferences.sql` — cidade/coordenadas e preferência do boletim meteorológico por usuário.

Alguns módulos também possuem `ensure_schema()` idempotente para tolerar implantação incremental. `weather_service.py` faz isso para `weather_preferences`, permitindo testar a branch mesmo antes de aplicar formalmente a migration no D1.

### Atenção a `runtime_schema.py`

O arquivo existe como compatibilidade/manual helper, mas **não é chamado pelo dispatcher atual**. Não trate sua lista de tabelas como catálogo completo do banco.

Ao criar tabela/coluna nova:

1. criar migration;
2. decidir se o caminho quente precisa de `ensure_schema()` defensivo;
3. atualizar este documento;
4. adicionar teste de regressão quando possível.

## 8. Contexto e memória: estado atual

Há duas gerações de arquitetura no repositório.

### Ativa

`conversation_layer.py` usa `natural_events` para referências operacionais curtas, por exemplo “essa tarefa”, e os handlers operacionais mantêm estado em `user_sessions`.

### Preservada, mas fora do dispatcher principal

A família abaixo existe no repositório, tem testes e pode servir de referência futura, mas não é chamada diretamente por `entry.py` hoje:

- `context_router.py`;
- `intent_parser.py`;
- `action_policy.py`;
- `context_memory.py`;
- `context_sync.py`;
- `suggestion_engine.py`;
- `library_catalog_handler.py`;
- `library_context_bridge.py`;
- boa parte da Butler Library e dos módulos `companion_*`/`cultural_*`.

O próprio `/health` registra `broad_nlu_disabled`, `generic_library_dispatch_disabled`, `cross_domain_suggestions_disabled` e `generic_personal_memory_disabled`.

**Não corrija uma falha de produção somente nesses módulos esperando efeito no bot.** Primeiro confirme que o dispatcher os chama.

## 9. Butler Library

Os dados de culinária, jogos, livros, filosofia e cultura pop continuam preservados em `cloudflare/src/knowledge/` e módulos auxiliares.

Hoje eles funcionam como acervo/reference code; o dispatcher genérico da Library não está habilitado na produção operacional. `docs/BUTLER_LIBRARY.md` documenta o desenho da camada e deve ser lido como arquitetura preservada/futura, não como lista de handlers atualmente ativos.

## 10. Runtime legado em `src/`

O diretório raiz `src/` usa:

- `python-telegram-bot`;
- polling;
- SQLite;
- `.env`;
- entrypoints `src/main.py` e `src/main_generic.py`.

Ele não deve receber correções de produção Cloudflare por padrão. Existe para referência/fallback e para histórico funcional.

Veja `src/README.md`.

## 11. Configuração

`cloudflare/src/settings.py` contém configuração versionada do deploy pessoal, incluindo perfil do proprietário, offset local e localização meteorológica padrão do proprietário.

Observações:

- schedulers usam `UTC_OFFSET_HOURS`; a integração Open-Meteo usa `TIMEZONE_NAME` para alinhar a previsão ao calendário local;
- `DEFAULT_WEATHER_CITY`, `DEFAULT_WEATHER_LATITUDE` e `DEFAULT_WEATHER_LONGITUDE` são fallback apenas para o proprietário;
- outros usuários precisam configurar explicitamente a cidade, por exemplo `clima em Salvador`;
- o perfil proprietário e a grade inicial ainda estão versionados em código;
- `TELEGRAM_WEBHOOK_SECRET` é suportado pelo webhook, mas opcional no `wrangler.jsonc` atual;
- mover dados pessoais/configuração para secrets ou seed privado é dívida técnica recomendada antes de tornar o repositório mais amplamente reutilizável.

## 12. Como descobrir a fonte de verdade antes de editar

Pergunte nesta ordem:

1. `worker.py`/`entry.py` importam o módulo?
2. algum módulo importado o chama transitivamente?
3. algum `install()` substitui a função depois?
4. um handler anterior consome a mensagem antes?
5. existe estado em `user_sessions` que muda o caminho?
6. o comportamento é scheduler ou webhook?
7. o teste existente cobre o caminho de produção ou apenas um módulo preservado?

Se uma dessas respostas não estiver clara, não altere o regex ou SQL ainda.
