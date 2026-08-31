# Butler — Status Atual e Handoff

**Data-base:** 31/08/2026  
**Branch de produção:** `main`  
**Etapa 1 — Linguagem natural:** ✅ concluída  
**Etapa 2 — Importação acadêmica confiável:** ✅ concluída  
**Etapa 3 — Auxiliares de Tempo / Modo Estudo:** ✅ concluída  
**Próxima fase oficial:** **Etapa 4 — Cursos e trilhas de estudo**  
**Snapshot técnico validado:** `83fe6e17a96c8b8734ba211d43f046670b3e9985`

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para runtime use `ARCHITECTURE.md`; para decisões duradouras use `CONTINUIDADE.md`; para ordem futura use `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`. Os fechamentos recentes estão em `ETAPA_2_GATE_FINAL.md`, `ETAPA_3A_ASSISTENTE_GERAL_TEMPO.md`, `ETAPA_3B_MODO_ESTUDO.md` e `ETAPA_3_ASSISTENTES_DE_TEMPO.md`.

---

## 1. O projeto em uma frase

Butler é um assistente pessoal multiusuário via Telegram para cotidiano, universidade, estudos, projetos e organização pessoal, com Core determinístico, linguagem natural conservadora, persistência D1 e serviços temporais redundantes via Durable Objects.

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
2. 🎓 Importação acadêmica confiável         ✅ concluída
3. ⏱️ Auxiliares de Tempo / Modo Estudo     ✅ concluída
4. 📚 Cursos e trilhas de estudo             ▶️ próxima etapa
   fechamento: menu por áreas da vida        ⏳ planejado
5. 📥 Caixa de entrada                       ⏳ planejada
6. 🗂️ Projetos e trabalho                    ⏳ planejada
7. 🧭 Resumo/contexto/priorização             ⏳ planejada
8. 🧠 Memória + Library seletiva             ⏳ planejada
9. 🔒 Hardening                              ⏳ planejada
10. 🌐 Abertura pública/capacidade/escala    ⏳ planejada
```

`TRILHA_DESENVOLVIMENTO_DEFINITIVA.md` continua sendo a autoridade da ordem/gates. Este arquivo é o snapshot operacional do ponto de continuidade.

---

## 3. Etapa 1 — resultado consolidado

A linguagem natural foi estruturada sem religar NLU ampla/opaca.

Ativos:

- `language_primitives.py` — famílias, relações, referências e polaridade sem CRUD;
- `short_context.py` — contexto curto de 30 min, isolamento e referências posicionais;
- `correction_patch.py` — correções como `não, 16h`, `quinta não, sexta`, correção de título e `desfaz`;
- `compound_router.py` — mensagens compostas, conjunções, preview e lote confirmado;
- `temporal_language.py` — classificação pura dos pedidos temporais rápidos.

Invariante:

```text
reconhecer linguagem ≠ autorizar escrita
```

Gate final: `docs/ETAPA_1_6_GATE_FINAL.md`.

---

## 4. Etapa 2 — resultado consolidado

### Decisão de produto

O formato acadêmico atual foi validado como suficiente e não foi remodelado.

Permanece:

```text
subjects
→ nome
→ ativa/trancada

subject_sessions
→ dia
→ início
→ fim
→ local
```

Etapa 2 focou apenas em aumentar a confiança da **primeira importação de novos usuários**.

`academic_import.py` agora faz:

```text
PDF textual/TXT
→ reconstrução conservadora
→ parse/validação
→ deduplicação
→ prévia
→ confirmação explícita
→ subjects + subject_sessions atuais
```

Qualquer trecho acadêmico ambíguo bloqueia toda a persistência daquela tentativa. O Butler prefere pedir correção a cadastrar uma grade incompleta como se estivesse correta.

Fonte SIGAA recomendada:

```text
Componente Curricular | Local | Horário
```

Sem OCR em produção.

Fechamento técnico:

- PR #30;
- merge `1542ec1e1f932fdcc75b32d097ddee0089ee2034`;
- regressão pós-merge: success, run #244.

Gate: `docs/ETAPA_2_GATE_FINAL.md`.

---

## 5. Etapa 3 — resultado consolidado

A Etapa 3 implementou dois domínios irmãos sobre o mesmo `PersonalAlarm`.

### 3A — Assistente Geral de Tempo

Exemplos:

```text
me lembra de desligar o ovo daqui a 5 minutos
tenho que ligar para alguém daqui a 10 minutos
me lembra daqui a 1 hora de tirar a roupa do varal
cronometra 30 minutos
```

Regras:

- tempo relativo curto tem prioridade sobre tarefa/lembrete tradicional quando a intenção está clara;
- quick timer não entra em `daily_items`;
- horizonte de 1 segundo a 24 horas;
- múltiplos timers simultâneos;
- cancelamento por texto/ID;
- isolamento por usuário;
- idempotência com `notification_log` + status próprio;
- Day-off não bloqueia timer explicitamente criado.

Persistência:

```text
0010_quick_timers.sql
quick_timers
```

Merge:

```text
PR #32
1165175c8868ff26a6b278473581519a8463191b
```

Pós-merge: success, run #247.

Documento: `docs/ETAPA_3A_ASSISTENTE_GERAL_TEMPO.md`.

### 3B — Modo Estudo

Exemplo:

```text
modo estudo Cálculo I: limites, derivadas, integrais
```

Padrão:

```text
25 min foco / 5 min pausa / 15 min pausa longa
```

Pode configurar, por exemplo:

```text
modo estudo 50/10/20 Física I: cinemática, dinâmica
```

Persistência:

```text
0011_study_mode.sql
study_sessions
study_topics
study_events
```

Invariante obrigatório e já testado:

**o tópico só avança quando o usuário explicitamente disser que concluiu ou pulou.**

Portanto fim do timer, pausa, restart e Day-off nunca criam conclusão fictícia.

Ações principais:

```text
concluí o tópico
pular tópico
não terminei
status estudo
pausar estudo
retomar estudo
cancelar estudo
histórico de estudo
```

O fim do foco só inicia pausa. Se o tópico continuar pendente, o próximo foco volta para ele.

O histórico usa eventos e estados persistidos; uma conclusão antecipada associa o fim do foco ao tópico realmente estudado.

Merge:

```text
PR #33
83fe6e17a96c8b8734ba211d43f046670b3e9985
```

Gate da PR: **330 testes passando**.  
Regressão pós-merge: **success**, run #251.

Documentos:

- `docs/ETAPA_3B_MODO_ESTUDO.md`;
- `docs/ETAPA_3_ASSISTENTES_DE_TEMPO.md`.

---

## 6. Scheduler e redundância

Existem duas linhas temporais complementares:

```text
Cron Trigger
+
Durable Objects (PersonalAlarm / AttendanceAlarm)
```

`PersonalAlarm` hoje considera:

```text
tarefas/compromissos/lembretes
quick timers
Modo Estudo
rotinas
resumos
```

No alarm:

```text
quick timers
→ study phases
→ reliable reminders
→ routines
→ summaries
→ rearme
```

`notification_log` continua sendo a barreira central de idempotência.

A reconciliação dos alarms ocorre fora do tempo crítico do webhook para preservar latência interativa.

Detalhes: `docs/SCHEDULER_REDUNDANCY.md`.

---

## 7. Performance

O caminho quente já possui:

- cache por update de `telegram_chat_id → user_id`;
- cache por update de `user_sessions`;
- gates lexicais antes de D1;
- DDL de presença removido do dispatcher geral;
- reconciliação de Durable Objects pós-resposta;
- Modo Estudo faz gate linguístico antes de consultar usuário/D1.

Se a latência voltar a incomodar, instrumentar tempo por handler/D1/Telegram antes de nova otimização.

---

## 8. Funcionalidades operacionais relevantes

Ativas:

- tarefas/pendências;
- compromissos;
- lembretes pessoais;
- agenda Hoje/Amanhã/7 dias;
- matérias/provas/presença/faltas;
- importação acadêmica confiável no primeiro acesso;
- rotinas e metas;
- mercado;
- musculação/progresso;
- Ler/Ver Depois: Livros, Filmes, Cursos e Outras;
- alertas rápidos/cronômetros;
- Modo Estudo;
- Day-off;
- resumos matinal/semanal;
- clima Open-Meteo com comentário humano;
- administração do proprietário;
- scheduler redundante.

`🎓 Cursos` em Ler/Ver Depois continua sendo backlog simples. Não confundir com a Etapa 4.

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
0009_ru_menu.sql
0010_quick_timers.sql
0011_study_mode.sql
```

Migration é fonte formal. `ensure_schema()` de domínio é somente defesa operacional.

---

## 10. Próxima etapa — Etapa 4

**Cursos e trilhas de estudo.**

Objetivo geral já definido no roadmap:

```text
Curso
→ módulos[]
   → conteúdos/submódulos[]
      → materiais[]
      → atividades[]
      → progresso
```

O progresso deve continuar explícito. Cursos autogeridos e cursos ao vivo possuem regras diferentes. O Modo Estudo da Etapa 3 será a infraestrutura operacional para executar sessões sobre um conteúdo de curso, sem misturar a identidade do curso com o cronômetro.

Ao final da Etapa 4 existe o fechamento obrigatório de reorganização do menu por áreas da vida antes da Etapa 5.

---

## 11. Instrução para a próxima IA

1. confirmar commits posteriores a `83fe6e17a96c8b8734ba211d43f046670b3e9985`;
2. ler `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
3. ler `docs/ETAPA_3_ASSISTENTES_DE_TEMPO.md` e os documentos 3A/3B;
4. iniciar **Etapa 4 — Cursos e trilhas de estudo**, sem criar roadmap paralelo;
5. preservar conclusão/progresso explícitos;
6. integrar cursos ao Modo Estudo sem transformar tempo em progresso;
7. manter `🎓 Cursos` de Ler/Ver Depois como backlog simples até a migração explícita de itens, se houver;
8. não reabrir o modelo acadêmico sem nova decisão do produto;
9. não religar Broad NLU/Library histórica como atalho.

**Próximo trabalho oficial: Etapa 4 — Cursos e trilhas de estudo.**
