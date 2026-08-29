<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram para organização de cotidiano, universidade, tarefas, compromissos, rotinas, metas, musculação, mercado, clima e acompanhamento pessoal.

A produção atual é determinística e roda em **Cloudflare Python Worker + Telegram Webhook + D1 + Durable Objects**. O repositório preserva experiências anteriores de NLU, memória e Library, mas essas camadas não devem ser confundidas com o dispatcher ativo.

## Documentação oficial

Antes de alterar o projeto, leia nesta ordem:

1. [`docs/BUTLER_DOSSIE_MESTRE.md`](docs/BUTLER_DOSSIE_MESTRE.md) — visão completa do produto, arquitetura, domínios, banco e regras;
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — fonte de verdade do runtime de produção;
3. [`docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`](docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md) — roadmap oficial;
4. [`docs/INVENTARIO_ETAPA_0.md`](docs/INVENTARIO_ETAPA_0.md) — classificação estrutural após a limpeza;
5. [`docs/MAINTAINER_GUIDE.md`](docs/MAINTAINER_GUIDE.md) — regras práticas de manutenção;
6. [`cloudflare/src/README.md`](cloudflare/src/README.md) — mapa técnico dos módulos;
7. [`CONTINUIDADE.md`](CONTINUIDADE.md) — decisões duradouras e histórico relevante.

`docs/AUDIT_MAIN_2026-08.md` permanece como registro histórico da auditoria que motivou a Etapa 0.

> **Importante:** a raiz `src/` é o runtime antigo de polling/SQLite. A produção está em `cloudflare/`.

---

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

Na Etapa 0, `entry.py` passou a expor funções testáveis para a orquestração real:

```text
dispatch_callback()
dispatch_message()
dispatch_scheduled()
```

A ordem de precedência é parte do contrato e possui regressão própria.

---

## Funcionalidades ativas

O Core operacional cobre:

- tarefas e pendências;
- compromissos e agenda;
- lembretes simples;
- matérias, grade, provas, presença e faltas;
- importação da grade do SIGAA por PDF/texto pesquisável;
- lista do que está faltando em casa;
- rotinas e metas;
- musculação, exercícios, séries, carga e progresso;
- Ler/Ver Depois;
- clima por usuário e previsão integrada ao resumo/agenda;
- Day-off;
- resumo matinal e fechamento semanal;
- alarmes persistentes para eventos críticos;
- diagnóstico administrativo de usuários;
- avisos administrativos com prévia e confirmação por botão.

Finanças continuam preservadas no Core, embora não sejam destaque no menu operacional atual.

O Butler é multiusuário: operações pessoais devem resolver `telegram_chat_id → user_id` e limitar SQL ao usuário correto.

---

## Menu principal

A fonte autoritativa é `cloudflare/src/operational_menu.py`:

```text
➕ Adicionar      🗓️ Hoje
🛒 Item faltando  📚 Matérias
🏠 Cotidiano      🏋️ Musculação
🌙 Day-off
```

Outros módulos reutilizam o menu sincronizado em `app.MAIN_KB`; não devem manter cópia concorrente do menu principal.

---

## Importação de grade do SIGAA

No primeiro acesso, o Butler orienta o usuário sobre o formato aceito. O modelo recomendado é a **tabela do painel principal do SIGAA** que contém:

```text
Componente Curricular | Local | Horário
```

Códigos como `35M45`, `24M23` ou `2T23` são relevantes para reconstruir dias e horários.

### Formatos aceitos

- PDF com texto pesquisável/selecionável;
- arquivo `.txt` contendo a grade.

### Formato recomendado

1. abra o painel principal do SIGAA onde aparecem matérias, locais e horários;
2. use **Imprimir → Salvar como PDF**;
3. confira que o texto continua selecionável;
4. no Butler, abra **📚 Matérias → 📥 Importar grade por PDF/texto**;
5. envie o arquivo e confira a prévia antes de confirmar.

Exemplo mínimo útil:

```text
Física II
PAV III, SALA 07
24M45
```

> Print, foto, imagem ou PDF escaneado não são o formato recomendado. O runtime atual não executa OCR.

A Etapa 2 do roadmap ampliará o motor de importação e a edição completa de matérias.

---

## Linguagem natural

A produção privilegia **fast paths conservadores e handlers por domínio**, não uma NLU ampla.

Exemplos esperados:

```text
me lembra de entregar o relatório amanhã às 18h
amanhã tenho dentista às 15h
acabou o café
segunda eu não vou pra Sistemas Digitais
hoje não vou conseguir treinar
cria uma rotina de estudar inglês
```

Ação explícita deve vencer palavra incidental de outro domínio. Exemplo: `me lembra de procurar jogos` é lembrete, não consulta de jogos.

A próxima etapa oficial é **Etapa 1 — Linguagem natural + estabilidade de conversa**, com foco em conjugações, conjunções, frases compostas, referências e sequências reais sem religar cegamente a NLU histórica.

---

## Lembretes e scheduler

O cron roda a cada minuto. Após a Etapa 0, `reliable_reminders.py` é a autoridade temporal única para `daily_items`:

- tarefa com horário: aviso no horário;
- compromisso: 5 minutos antes;
- lembrete pessoal simples: no horário, com tolerância curta;
- `notification_log`: idempotência;
- entrega crítica validada quando aplicável.

O cron operacional:

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ app.scheduled_tick (compatibilidade)
```

Aula/presença e alarmes pessoais possuem mecanismos próprios, incluindo Durable Objects.

A Etapa 0 removeu a antiga cadeia duplicada de scheduler em `quality_patch.py`/`conversation_layer.py` e apagou `reminder_policy.py`, que havia se tornado apenas um `noop` de compatibilidade.

---

## Banco de dados

A fonte formal do D1 são as migrations:

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

`ensure_schema()` pode existir como proteção incremental, mas não substitui migration.

`runtime_schema.py` é helper preservado e não representa o bootstrap automático do banco.

Migration destrutiva exige backup/export D1 e plano de rollback documentado.

---

## Administração

Comandos administrativos são restritos ao proprietário.

Exemplos:

```text
/status usuarios
/aviso Nova funcionalidade disponível
/aviso id 2 Mensagem individual
```

`/aviso` mostra uma prévia e botões:

```text
✅ Confirmar envio
❌ Cancelar
```

O aviso pendente possui estado no D1 e proteção contra confirmação repetida.

---

## Clima

O Butler usa Open-Meteo sem chave de API para a previsão.

- proprietário possui localização padrão configurada;
- outros usuários configuram sua cidade;
- resumo matinal pode incluir clima;
- `Hoje`/`Amanhã` podem combinar agenda + previsão;
- falha do serviço meteorológico não derruba agenda/resumo.

---

## Código preservado

Existe trabalho histórico útil em:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
compound_router.py
suggestion_engine.py
deterministic_memory.py
butler_library.py
library_catalog_handler.py
knowledge/
companion_*
conversational_*
```

Esses componentes **não formam o roteador central de produção hoje**. Servirão como material para as futuras Etapas 1 e 7 somente após avaliação e testes.

A raiz `src/` também permanece preservada como runtime histórico.

---

## Limpeza da Etapa 0

A fase “arrumar a casa” realizou, entre outros pontos:

- Dossiê Mestre;
- inventário/classificação do runtime;
- dispatcher, callbacks e cron testáveis;
- uma fonte autoritativa para o menu principal;
- uma autoridade temporal para lembretes de `daily_items`;
- migration formal para Ler/Ver Depois;
- remoção de `add_intent_patch.py` por desuso comprovado;
- remoção de `reminder_policy.py` após eliminação da duplicidade que ele neutralizava;
- documentação de dívida técnica e política de backup.

Detalhes: [`docs/INVENTARIO_ETAPA_0.md`](docs/INVENTARIO_ETAPA_0.md).

---

## Testes

Na pasta `cloudflare/`:

```bash
pytest -q
```

O workflow do GitHub Actions:

1. compila `cloudflare/src`;
2. executa a regressão determinística;
3. protege, entre outros contratos, a ordem do dispatcher/callbacks/cron.

A produção usa Pyodide; os testes CPython possuem stubs mínimos de `js`, `pyodide` e `workers`, sem simular rede real.

---

## Regra para novas mudanças

Antes de criar outro `*_patch.py` ou `*_fix.py`:

1. encontre o módulo autoritativo;
2. verifique se a mudança cabe diretamente nele;
3. proteja com teste;
4. use camada paralela somente se houver limitação técnica real;
5. documente qualquer monkeypatch novo.

A ideia daqui para frente é **evoluir funcionalidades sem voltar a acumular uma arquitetura difícil de explicar**.
