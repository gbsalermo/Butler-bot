<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal multiusuário via Telegram para cotidiano, universidade, estudo, cursos, projetos, trabalho, hábitos, treino e organização pessoal.

A produção roda em **Cloudflare Python Worker + Telegram Webhook + D1 + Durable Objects**. O repositório preserva experiências históricas de NLU/memória/Library, mas elas não devem ser confundidas com o dispatcher ativo.

## Estado atual

**Data-base documental:** 02/09/2026  
**Etapas 0–3:** ✅ concluídas  
**Etapa 4 — Cursos e trilhas:** ✅ subetapas 4.1–4.6 concluídas  
**Fechamento da Etapa 4:** ▶️ menu minimalista implementado, aguardando validação de produção

O snapshot de handoff está em [`docs/STATUS_ATUAL.md`](docs/STATUS_ATUAL.md). Uma nova IA/agente deve começar por ele e continuar o roadmap existente, sem criar outro.

## Roadmap

```text
0. 🧹 Arrumar a casa                         ✅
1. 🗣️ Linguagem natural + conversa real     ✅
2. 🎓 Importação acadêmica confiável         ✅
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ✅
4. 📚 Cursos e trilhas de estudo             ▶️ fechamento em validação
   4.1 Modelo + autoridade                   ✅
   4.2 CRUD + navegação                      ✅
   4.3 Progresso / Continuar curso           ✅
   4.4 Integração com Modo Estudo            ✅
   4.5 Importação                            ✅
   4.6 Gate final                            ✅
   fechamento: menu minimalista              ▶️ validar em produção
5. 📥 Caixa de entrada                       ⏳
6. 🗂️ Projetos e trabalho                    ⏳
7. 🧭 Resumo/contexto/priorização             ⏳
8. 🧠 Memória + Library seletiva             ⏳
9. 🔒 Hardening                              ⏳
10. 🌐 Abertura pública/capacidade/escala    ⏳
11. 🌍 Idiomas e internacionalização          ⏳
```

Não iniciar a Etapa 5 antes da validação e fechamento oficial da nova navegação.

## Documentação oficial

Leia nesta ordem:

1. [`docs/STATUS_ATUAL.md`](docs/STATUS_ATUAL.md) — andamento e próximo trabalho;
2. [`CONTINUIDADE.md`](CONTINUIDADE.md) — decisões duradouras;
3. [`docs/BUTLER_DOSSIE_MESTRE.md`](docs/BUTLER_DOSSIE_MESTRE.md) — visão completa do produto;
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — runtime de produção;
5. [`docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`](docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md) — ordem oficial;
6. [`docs/ETAPA_4_FECHAMENTO_MENU_MINIMALISTA.md`](docs/ETAPA_4_FECHAMENTO_MENU_MINIMALISTA.md) — decisão e inventário do fechamento;
7. [`docs/MANUAL_USUARIO.md`](docs/MANUAL_USUARIO.md) — uso do produto;
8. [`docs/MAINTAINER_GUIDE.md`](docs/MAINTAINER_GUIDE.md) — manutenção.

> **Importante:** a raiz `src/` é o runtime antigo de polling/SQLite. Produção está em `cloudflare/`.

## Runtime de produção

```text
Telegram
   ↓ webhook
cloudflare/src/worker.py
   ↓
cloudflare/src/entry.py
   ↓
handlers operacionais ordenados
   ↓
D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A precedência do dispatcher é parte do contrato e possui regressão própria.

## Funcionalidades ativas

O Core cobre, entre outros:

- tarefas, compromissos e lembretes;
- rotinas e metas;
- matérias, grade, provas, edição de provas, presença/faltas;
- importação acadêmica por PDF textual/TXT;
- quick timers/alertas;
- Modo Estudo;
- musculação;
- lista de itens faltando;
- cardápio do RU;
- Interesses/Ler-Ver Depois;
- clima e resumos;
- Day-off;
- diagnóstico/admin;
- linguagem natural conservadora e contexto curto;
- Cursos estruturados, atualmente em standby para usuários comuns.

Finanças permanecem preservadas no Core, embora não sejam destaque da navegação atual.

## Menu principal atual

A fonte autoritativa é `cloudflare/src/operational_menu.py`. A versão minimalista aprovada é:

```text
➕ Adicionar          🗓️ Hoje
🎓 Faculdade          📋 Minha vida
🏋️ Treino             ⚙️ Mais
🌙 Day-off
```

Áreas:

```text
🎓 Faculdade
├── 📚 Matérias
├── 🍽️ RU
├── 🧠 Modo Estudo
└── 📘 Cursos   (standby / owner-only)

📋 Minha vida
├── ✅ Tarefas
├── 📅 Compromissos
├── 🧘 Rotinas
├── 🎯 Metas
├── 🛒 Casa
└── 📌 Interesses

⚙️ Mais
├── 👤 Como me chamar
└── 📖 Manual
```

`🏋️ Treino` abre diretamente o menu de musculação. `🌙 Day-off` permanece sozinho na última linha. Rótulos antigos são aceitos temporariamente como aliases para não quebrar teclados já renderizados no Telegram.

## Cursos estruturados — standby

O domínio estruturado `📘 Cursos` é diferente da categoria `🎓 Cursos` dentro de `📌 Interesses`.

Enquanto o recurso passa por nova estabilização, `📘 Cursos` continua visível apenas ao proprietário. A filtragem ocorre na fronteira do Telegram, evitando expor o botão a usuários comuns.

Autoridade de persistência:

```text
cloudflare/src/course_domain.py
```

Camadas operacionais:

```text
course_operational.py   → CRUD/navegação
course_stage4.py        → progresso, continuar, Modo Estudo e wizard de importação
course_study_bridge.py  → ponte Cursos ↔ Modo Estudo
course_importer.py      → parser/prévia/importação
```

Regras centrais:

```text
abrir/navegar ≠ concluir
Continuar curso ≠ concluir
tempo estudado ≠ concluir
fim do Modo Estudo ≠ concluir
último conteúdo resolvido ≠ concluir curso
prévia de importação ≠ persistir
```

Progresso e conclusão exigem ações explícitas.

## Linguagem e contexto

Produção privilegia handlers determinísticos, famílias linguísticas compartilhadas e contexto curto, não uma NLU ampla.

Ativos principais:

```text
language_primitives.py
short_context.py
correction_patch.py
compound_router.py
temporal_language.py
```

Regra permanente:

```text
reconhecer linguagem ≠ autorizar escrita
```

A navegação por áreas serve como descoberta e fallback. Frases naturais continuam funcionando sem o usuário abrir primeiro a área correspondente.

## Lembretes e scheduler

Cron não é o único relógio. O Butler usa também Durable Objects (`PersonalAlarm` e `AttendanceAlarm`). `notification_log` é a barreira central de idempotência para entregas agendadas.

`reliable_reminders.py` continua sendo autoridade temporal para `daily_items`. Lembretes de prova têm marcos em 7/3/1 dias, dia da prova e última hora, com recuperação segura no mesmo dia quando necessário.

## Banco de dados

Migrations formais atuais:

```text
0001_initial.sql
0002_app_state.sql
0003_attendance.sql
0004_conversation_context.sql
0005_goal_profiles.sql
0006_weather_preferences.sql
0007_admin_pending_announcements.sql
0008_later_items.sql
0009_ru_menu.sql
0010_quick_timers.sql
0011_study_mode.sql
0012_runtime_errors.sql
0013_courses.sql
0014_course_study_links.sql
```

`cloudflare/migrations/` é a fonte formal do D1. `ensure_schema()` é apenas tolerância operacional.

## Testes

Na pasta `cloudflare/`:

```bash
pytest -q
```

O GitHub Actions compila `cloudflare/src` e executa a regressão determinística. O fechamento minimalista adiciona cobertura específica em:

```text
test_stage4_menu_minimalista.py
```

Além dos gates funcionais anteriores da Etapa 4.

**CI verde é condição necessária, mas não prova deploy Cloudflare.** O build/deploy de `salbutler-bot` deve ser conferido separadamente.

## Regra para novas mudanças

Antes de criar outro `*_patch.py`/`*_fix.py`:

1. encontre o módulo autoritativo;
2. veja se a mudança cabe nele;
3. proteja com teste;
4. use ponte/camada paralela só quando houver fronteira real entre domínios;
5. documente monkeypatches necessários.

Antes de qualquer nova etapa, consulte `docs/STATUS_ATUAL.md` e o último gate concluído.
