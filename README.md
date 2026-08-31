<p align="center">
  <img src="assets/butler.png" alt="Butler - mascote" width="420">
</p>

# Butler Bot

**Butler** é um assistente pessoal via Telegram para organização de cotidiano, universidade, tarefas, compromissos, rotinas, metas, musculação, mercado, clima e acompanhamento pessoal.

A produção atual é determinística e roda em **Cloudflare Python Worker + Telegram Webhook + D1 + Durable Objects**. O repositório preserva experiências anteriores de NLU, memória e Library, mas essas camadas não devem ser confundidas com o dispatcher ativo.

## Estado atual

**Data-base documental:** 31/08/2026  
**Fase oficial:** Etapa 1 — Linguagem natural + estabilidade de conversa real  
**Subetapa atual:** **1.4 — Correção e auto-reparo conversacional**

Já concluído na Etapa 1:

- **1.1:** auditoria da linguagem ativa + corpus inicial;
- **1.2:** base linguística comum em `language_primitives.py`;
- **1.3:** contexto curto/referências com `short_context.py`;
- **1.4:** primeira fatia temporal já mesclada, permitindo corrigir o item recém-criado sem duplicá-lo (`não, 16h`, `quis dizer terça`, etc.).

O snapshot de handoff está em [`docs/STATUS_ATUAL.md`](docs/STATUS_ATUAL.md). Uma nova IA/agente deve começar por ele e **continuar a etapa atual**, sem criar outro roadmap.

## Documentação oficial

Antes de alterar o projeto, leia nesta ordem:

1. [`docs/STATUS_ATUAL.md`](docs/STATUS_ATUAL.md) — onde o projeto está agora e o próximo trabalho;
2. [`docs/BUTLER_DOSSIE_MESTRE.md`](docs/BUTLER_DOSSIE_MESTRE.md) — visão completa do produto, arquitetura, domínios, banco e regras;
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — fonte de verdade do runtime de produção;
4. [`docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`](docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md) — roadmap oficial;
5. [`docs/ETAPA_1_4_CORRECOES.md`](docs/ETAPA_1_4_CORRECOES.md) — trabalho funcional atualmente aberto;
6. [`docs/SCHEDULER_REDUNDANCY.md`](docs/SCHEDULER_REDUNDANCY.md) — arquitetura de contingência temporal após o incidente de 30/08;
7. [`docs/INVENTARIO_ETAPA_0.md`](docs/INVENTARIO_ETAPA_0.md) — classificação estrutural após a limpeza;
8. [`docs/MAINTAINER_GUIDE.md`](docs/MAINTAINER_GUIDE.md) — regras práticas de manutenção;
9. [`cloudflare/src/README.md`](cloudflare/src/README.md) — mapa técnico dos módulos;
10. [`CONTINUIDADE.md`](CONTINUIDADE.md) — decisões duradouras e histórico relevante.

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

`entry.py` expõe funções testáveis para a orquestração real:

```text
dispatch_callback()
dispatch_message()
dispatch_scheduled()
```

A ordem de precedência é parte do contrato e possui regressão própria.

Após a Etapa 1.3/1.4, o caminho de linguagem ativa também possui:

```text
language_primitives.py  → famílias linguísticas/polaridade sem efeitos colaterais
short_context.py        → contexto curto expirável e isolado por usuário
correction_patch.py     → auto-reparo seguro do item recém-criado
```

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
- Ler/Ver Depois, com categorias **Livros, Filmes, Cursos e Outras**;
- clima por usuário e previsão integrada ao resumo/agenda;
- comentários mais naturais sobre a previsão sem alterar os dados objetivos do Open-Meteo;
- Day-off;
- resumo matinal e fechamento semanal;
- alarmes persistentes para eventos críticos;
- redundância de scheduler via Durable Objects;
- diagnóstico administrativo de usuários;
- avisos administrativos com prévia e confirmação por botão;
- linguagem natural operacional conservadora;
- referências de contexto curto;
- primeira fatia de correção temporal conversacional.

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

A produção privilegia **fast paths conservadores, famílias linguísticas compartilhadas e handlers por domínio**, não uma NLU ampla.

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

O contexto curto ativo expira e é isolado por usuário. Referências como `ela`, `essa`, `a segunda`, `a anterior` podem resolver itens recentes quando o contexto é seguro.

A subetapa atual, **1.4**, trabalha correção do turno anterior sem duplicar registros. Depois dela, os gates restantes da Etapa 1 incluem principalmente conjunções, mensagens compostas/múltiplas intenções, corpus maior e sequências mais longas.

---

## Lembretes e scheduler

O Cron Trigger roda a cada minuto, mas **não é mais o único relógio do sistema**.

Linha primária:

```text
cron
→ day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ app.scheduled_tick (compatibilidade)
```

Linha persistente de contingência:

```text
webhook/cron
→ sync_personal_alarms()
→ PersonalAlarm por usuário
→ próximo evento persistido no Durable Object
→ dispatchers autoritativos
```

`AttendanceAlarm` continua separado para presença/aula.

Após webhook, a reconciliação dos alarms usa `ctx.waitUntil(...)`, fora do caminho crítico da resposta HTTP. Isso reduz latência sem perder o rearme persistente.

`reliable_reminders.py` continua sendo a autoridade temporal única para `daily_items`:

- tarefa com horário: aviso no horário;
- compromisso: 5 minutos antes;
- lembrete pessoal simples: no horário, com tolerância curta;
- `notification_log`: idempotência;
- entrega crítica validada quando aplicável.

A redundância de Cron + Durable Object não deve gerar duplicidade; ambos convergem para dispatchers autoritativos e a mesma barreira de idempotência.

Detalhes: [`docs/SCHEDULER_REDUNDANCY.md`](docs/SCHEDULER_REDUNDANCY.md).

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

As subetapas 1.1–1.4 reutilizam estruturas existentes e, neste snapshot, não introduziram migration nova.

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
- falha do serviço meteorológico não derruba agenda/resumo;
- `weather_personality.py` pode acrescentar comentário humano/descontraído sem inventar dados meteorológicos.

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

Esses componentes **não formam o roteador central de produção hoje**. Servirão como material para etapas futuras somente após avaliação e testes.

A raiz `src/` também permanece preservada como runtime histórico.

---

## Testes e desempenho

Na pasta `cloudflare/`:

```bash
pytest -q
```

O workflow do GitHub Actions:

1. compila `cloudflare/src`;
2. executa a regressão determinística;
3. protege, entre outros contratos, a ordem do dispatcher/callbacks/cron.

A produção usa Pyodide; os testes CPython possuem stubs mínimos de `js`, `pyodide` e `workers`, sem simular rede real.

O caminho quente também possui regressões específicas para:

- cache local ao update de `telegram_chat_id → user_id`;
- cache local ao update de `user_sessions`;
- gates antes de consultas D1 irrelevantes;
- ausência de DDL de presença no dispatcher geral;
- reconciliação de Durable Objects fora do tempo de resposta do webhook.

CI verde é condição necessária para merge, mas não prova deploy Cloudflare.

---

## Regra para novas mudanças

Antes de criar outro `*_patch.py` ou `*_fix.py`:

1. encontre o módulo autoritativo;
2. verifique se a mudança cabe diretamente nele;
3. proteja com teste;
4. use camada paralela somente se houver limitação técnica real;
5. documente qualquer monkeypatch novo.

Antes de iniciar uma etapa nova, consulte `docs/STATUS_ATUAL.md` e o gate da etapa atual. A ideia daqui para frente é **evoluir funcionalidades sem voltar a acumular uma arquitetura difícil de explicar**.
