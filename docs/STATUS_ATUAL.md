# Butler — Status Atual e Handoff

**Data-base:** 31/08/2026  
**Branch de produção:** `main`  
**Snapshot técnico validado:** `f08bff2e4edf5303f8b79a5a420ecd80356043fa`  
**Fase concluída:** **Etapa 1 — Linguagem natural + estabilidade de conversa real**  
**Próxima fase oficial:** **Etapa 2 — Acadêmico completo + importação robusta**

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para runtime use `ARCHITECTURE.md`; para decisões duradouras use `CONTINUIDADE.md`; para ordem futura use `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram que combina organização cotidiana, universidade, tarefas, compromissos, rotinas, metas, musculação, mercado, clima e acompanhamento temporal confiável, mantendo operações críticas determinísticas e linguagem natural conservadora.

Produção:

```text
Telegram
→ webhook
→ Cloudflare Python Worker
→ cloudflare/src/worker.py
→ cloudflare/src/entry.py
→ handlers operacionais
→ D1 / Durable Objects / Telegram Bot API / Open-Meteo
```

A raiz `src/` continua histórica/preservada e não governa produção.

---

## 2. Estado do roadmap

```text
0. 🧹 Arrumar a casa                         ✅ concluída
1. 🗣️ Linguagem natural + conversa real     ✅ concluída
2. 🎓 Acadêmico + importação robusta         ▶️ próxima etapa
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ⏳ planejada
4. 📚 Cursos e trilhas de estudo             ⏳ planejada
   fechamento: menu por áreas da vida        ⏳ planejado
5. 📥 Caixa de entrada                       ⏳ planejada
6. 🗂️ Projetos e trabalho                    ⏳ planejada
7. 🧭 Resumo/contexto/priorização             ⏳ planejada
8. 🧠 Memória + Library seletiva             ⏳ planejada
9. 🔒 Hardening                              ⏳ planejada
10. 🌐 Abertura pública/capacidade/escala    ⏳ planejada
```

### Etapa 1 — concluída

| Subetapa | Status | Resultado principal |
|---|---|---|
| 1.1 Auditoria da linguagem | ✅ | mapa da linguagem ativa, corpus e primitivas determinísticas |
| 1.2 Base Linguística Comum | ✅ | famílias compartilhadas, polaridade e redução de parsers concorrentes |
| 1.3 Referências + Contexto Curto | ✅ | `short_context.py`, expiração, isolamento, referências e listas posicionais |
| 1.4 Correção / Auto-reparo | ✅ | correção temporal/título, elipse e rollback seguro sem duplicar item |
| 1.5 Frases compostas | ✅ | conjunções, preview e lote seguro de 2–5 ações com confirmação |
| 1.6 Conversas completas | ✅ | integração multi-turno, dois usuários, expiração, barreira de assunto e gate final |

Documento final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 3. O que a Etapa 1 deixou ativo

### Base linguística

`language_primitives.py` reconhece famílias, relações, referências, correções e polaridade sem acessar D1, Telegram ou CRUD.

Regra permanente:

```text
reconhecer linguagem ≠ autorizar escrita
```

### Contexto curto

`short_context.py` é a autoridade do contexto operacional curto:

- janela padrão de 30 minutos;
- isolamento por `user_id`;
- barreira de mudança de assunto;
- `essa/ela/ele/a anterior/a outra`;
- `a primeira/a segunda/a terceira` usando a ordem realmente mostrada;
- lista candidata preservada entre referências sequenciais somente quando o foco continua dentro da mesma lista;
- item novo fora da lista não herda candidatos antigos.

### Auto-reparo

`correction_patch.py` suporta, quando o alvo recente é seguro:

```text
não, 16h
quinta não, sexta
não é dentista, é oftalmo
dentista não, oftalmo
deixa como tava / desfaz
```

O mesmo registro é alterado; contexto vindo de lista não é corrigido silenciosamente.

### Frases compostas

`compound_router.py` é agora uma camada neutra. O roteador histórico que misturava acadêmico/culinária/pets não deve ser reativado.

Proteções:

```text
me lembra de comprar pão e leite
→ um lembrete

tenho reunião com João e Maria
→ um compromisso

tenho aula porque tenho que trabalhar
→ a causa não vira tarefa automática

tenho aula ou tenho dentista
→ alternativa; não executa os dois lados
```

Quando existem **2 a 5** tarefas/compromissos/lembretes simples completamente determinados, o Butler mostra preview e oferece:

```text
✅ Registrar tudo
❌ Cancelar lote
```

O lote:

- é pré-validado integralmente;
- expira em 10 minutos;
- revalida datas/horários na confirmação;
- usa um único `INSERT` multi-values em `daily_items`;
- preserva grafia/acentos originais;
- grava a ordem criada no contexto curto.

6+ ações não entram no lote automático.

### Tempo relativo preparado, mas ainda não executado

`temporal_language.py` reconhece semanticamente:

```text
me lembra de desligar o ovo daqui a 5 minutos
→ relative_alert / 300 s

cronometra 30 minutos
→ timer / 1800 s
```

Isso **não deve virar tarefa normal**. A execução persistente pertence à Etapa 3 — Assistente Geral de Tempo.

---

## 4. Próxima etapa: Etapa 2

Objetivo: consolidar o domínio acadêmico e a importação antes de Modo Estudo/Cursos.

Prioridades já definidas:

1. edição completa de matéria;
2. múltiplos horários/localizações sem duplicação artificial;
3. modelo acadêmico normalizado;
4. importação como pipeline `fonte → adaptador → estrutura → validação → prévia → confirmação → persistência`;
5. SIGAA como primeiro adaptador oficial;
6. onboarding explicando o formato aceito/recomendado;
7. presença continua explícita — aula prevista nunca implica presença.

Fonte SIGAA recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitar PDF com texto pesquisável e TXT; produção não deve depender de OCR.

**Não avançar para a Etapa 3 antes de fechar o gate acadêmico da Etapa 2.**

---

## 5. Dispatcher e autoridades

Ordem simplificada de mensagens:

```text
/start/reset
→ admin/diagnósticos
→ despedida prioritária
→ usabilidade/Ler-Ver Depois
→ menu/rotinas/presença UI/navegação
→ core_fast_path
   → clima contextual
   → compound_router antes das ações únicas
   → lembrete/tarefa/compromisso/etc.
→ presença/provas/acadêmico
→ correction_patch
→ referência curta
→ contexto de tarefa
→ guards/mercado/quality/musculação
→ conversation_layer
→ app.py somente para botão/estado guiado
→ fallback
```

Cron:

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ legacy compatibility
```

Autoridades importantes:

- `entry.py`: precedência;
- `operational_menu.py`: menu principal;
- `reliable_reminders.py`: política temporal de `daily_items`;
- `short_context.py`: contexto curto;
- `language_primitives.py`: sinais linguísticos compartilhados;
- `compound_router.py`: estrutura de mensagens compostas;
- `correction_patch.py`: auto-reparo recente seguro.

Broad NLU, Library genérica, memória pessoal ampla e sugestões transversais permanecem desativadas como dispatcher central.

---

## 6. Scheduler e redundância

Após o incidente de 30/08/2026, há duas linhas temporais:

```text
Cron Trigger
→ dispatch_scheduled()

Durable Objects
→ PersonalAlarm / AttendanceAlarm
→ mesmos dispatchers autoritativos
```

O usuário validou em produção que o fallback de Durable Object disparou e que o heartbeat do Cron voltou a avançar.

`notification_log` continua sendo barreira de idempotência.

No webhook, reconciliação de alarms usa trabalho pós-resposta para não bloquear o caminho interativo.

Detalhes: `docs/SCHEDULER_REDUNDANCY.md`.

---

## 7. Performance

O caminho quente já recebeu:

- cache por update de `telegram_chat_id → user_id`;
- cache por update de `user_sessions`;
- gates lexicais antes de D1 em módulos de contexto/metas/Ler-Ver Depois;
- DDL de presença removido do dispatcher geral;
- sincronização de Durable Objects fora do tempo de resposta do webhook.

O cache não persiste entre updates.

Se latência voltar a ser problema, o próximo passo é **instrumentação por handler/D1/Telegram**, não otimização aleatória.

---

## 8. Funcionalidades operacionais relevantes

Ativas no Core:

- tarefas/pendências;
- compromissos;
- lembretes pessoais;
- agenda Hoje/Amanhã/7 dias;
- matérias/provas/presença/faltas;
- importação acadêmica atual por PDF textual/TXT;
- rotinas e metas;
- mercado/itens faltando;
- musculação/progresso;
- Ler/Ver Depois com Livros, Filmes, Cursos e Outras;
- Day-off;
- resumos matinal/semanal;
- clima Open-Meteo com apresentação mais humana;
- recursos administrativos do proprietário;
- scheduler redundante.

A categoria `Cursos` de Ler/Ver Depois é backlog simples, não o módulo de Cursos/Trilhas da Etapa 4.

---

## 9. Banco e migrations

Migrations formais conhecidas:

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

A Etapa 1 reutilizou estruturas existentes (`natural_events`, `user_sessions`, `daily_items`) e não exigiu migration nova para linguagem/contexto.

Migration é fonte formal; `ensure_schema()` é defesa operacional, não substituto.

---

## 10. Regressão e validação

Fechamento da Etapa 1:

- PR #23: conclusão da 1.4;
- PR #24: análise/preview de frases compostas;
- PR #25: confirmação/persistência segura em lote;
- PR #26: gate final da 1.5;
- PR #27: conversas completas / 1.6;
- merge técnico final da Etapa 1: `f08bff2e4edf5303f8b79a5a420ecd80356043fa`;
- regressão pós-merge da `main`: **success**.

CI verde comprova regressão do repositório; não prova sozinho que o commit já está implantado na Cloudflare.

---

## 11. Instrução para a próxima IA

1. confirmar commits posteriores a este snapshot;
2. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
3. ler documentos acadêmicos e `ARCHITECTURE.md`;
4. iniciar **Etapa 2**, sem criar novo roadmap;
5. tratar correção urgente de produção quando necessário e retornar ao gate acadêmico;
6. não religar NLU/Library histórica como atalho.

**Próximo trabalho oficial: Etapa 2 — Acadêmico completo + importação robusta.**
