# Runtime legado — `src/`

> **Atenção:** este diretório não é o runtime de produção atual do Butler.

A produção está em `cloudflare/` e usa Telegram Webhook + Cloudflare Python Worker + D1.

Este diretório preserva a implementação anterior baseada em:

- `python-telegram-bot`;
- polling;
- SQLite;
- `.env` local;
- entrypoints `src/main.py` e `src/main_generic.py`.

## Quando usar este diretório

- consultar comportamento histórico;
- comparar uma funcionalidade antiga com a versão Cloudflare;
- usar como fallback local quando isso for uma decisão explícita;
- recuperar lógica que ainda não foi portada.

## Quando NÃO usar

Não faça uma correção aqui esperando alterar o Butler implantado em produção.

Para produção, comece em:

```text
cloudflare/src/worker.py
cloudflare/src/entry.py
```

Leia também:

```text
docs/ARCHITECTURE.md
docs/MAINTAINER_GUIDE.md
cloudflare/src/README.md
```

## Entry points

### `main.py`

Runtime pessoal antigo. Inicializa tabelas SQLite, registra handlers do `python-telegram-bot` e executa `run_polling()`.

### `main_generic.py`

Variante multiusuário/genérica antiga. Usa outro arquivo `.env`/SQLite e não é equivalente ao perfil genérico do Worker atual.

## Mapa resumido

| Grupo | Arquivos principais | Papel |
|---|---|---|
| Inicialização | `main.py`, `main_generic.py`, `config.py` | processo de polling e configuração local |
| Banco | `database.py`, `daily_store.py`, `home_store.py`, `finance_store.py`, `natural_store.py` | persistência SQLite |
| Tarefas/agenda | `bot_handlers.py`, `quick_capture.py`, `history_handlers.py`, `scheduler.py` | ações cotidianas e avisos |
| Acadêmico | `academic_navigation.py`, `schedule_importer.py`, `schedule_import_handlers.py`, `sigaa_schedule.py` | matérias/grade/importação |
| Casa | `home_handlers.py`, `home_menu.py`, `home_store.py` | mercado e cotidiano doméstico |
| Finanças | `finance_handlers.py`, `finance_store.py` | entradas, saídas e relatórios |
| Linguagem | `natural_language.py`, `natural_handlers.py`, `casual_handlers.py` | NLU/fallback antigos |
| Personalidade | `personality.py`, `personality_navigation.py`, `behavior_engine.py`, `behavior_handlers.py` | comportamento antigo |
| Musculação | `protocol_mass_*`, `workout_import_*` | protocolo pessoal e ficha importada |
| Bem-estar | `wellbeing_handlers.py`, `lifestyle_handlers.py`, `morning_context.py` | hábitos/contexto pessoal |
| UI/Navegação | `assistant_views.py`, `quick_access.py`, `ui_layout.py` | teclados e telas de polling |
| Multiusuário | `user_scope.py`, `onboarding.py` | escopo antigo por chat |
| Ler/Ver Depois | `later_handlers.py` | lista persistente antiga |

## Regra de manutenção

Se uma funcionalidade existe nos dois runtimes, o código Cloudflare é a fonte de verdade para produção. Só mantenha os dois sincronizados quando houver uma razão explícita; caso contrário, documente a divergência em vez de duplicar correções silenciosamente.
