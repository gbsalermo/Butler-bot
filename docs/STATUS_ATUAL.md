# Butler — Status Atual e Handoff

**Data-base:** 31/08/2026  
**Branch de produção:** `main`  
**Snapshot técnico validado da Etapa 1:** `f08bff2e4edf5303f8b79a5a420ecd80356043fa`  
**Handoff documental da Etapa 1:** `e3220d95aed43b1e5730709e56aa07d6716e77d9`  
**Fase oficial:** **Etapa 2 — Acadêmico completo + importação robusta**  
**Subetapa em andamento:** **2.1 — Inventário e autoridades acadêmicas**

> Este é o primeiro arquivo para uma nova IA/agente consultar ao assumir o Butler. Para runtime use `ARCHITECTURE.md`; para decisões duradouras use `CONTINUIDADE.md`; para ordem futura use `TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`. O inventário acadêmico atual está em `ETAPA_2_1_INVENTARIO_ACADEMICO.md`.

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
2. 🎓 Acadêmico + importação robusta         🚧 em andamento — 2.1
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

## 3. Etapa 2.1 — achados atuais

O modelo acadêmico formal atual é mínimo:

```text
subjects
→ id, user_id, name, active, created_at

subject_sessions
→ id, subject_id, weekday, start_time, end_time, location
```

Presença/faltas já possuem estruturas próprias em `0003_attendance.sql`.

O inventário identificou os seguintes riscos prioritários:

1. **P0 — importação destrutiva:** a confirmação atual da grade apaga todas as matérias/sessões do usuário e recria tudo;
2. **P0 — histórico de faltas:** como faltas referenciam matéria/sessão com `ON DELETE CASCADE`, reimportar pode apagar histórico;
3. **P0 — provas:** hoje usam `daily_items.details = exam:<subject_id>`; recriar matérias pode deixar provas semanticamente órfãs;
4. **P1 — código SIGAA descartado:** `parse_schedule_text()` já extrai `code`, mas o schema não o persiste;
5. **P1 — sessões sem unicidade formal:** importações incrementais podem duplicar aula;
6. **P1 — edição existe por monkeypatch:** `academic_polish.py` governa a edição final apesar de `app.py` ainda conter fluxo-base antigo;
7. **P1 — remover matéria é DELETE:** a política de arquivar/trancar/remover precisa ser definida antes da evolução do modelo.

**Decisão:** não criar migration acadêmica nova antes de fechar a 2.2 — identidade/modelo acadêmico.

---

## 4. Autoridades acadêmicas atuais

- `app.py`: cadastro-base, parser SIGAA, importação/preview/persistência atual;
- `academic_polish.py`: edição guiada real e onboarding SIGAA via monkeypatch instalado;
- `academic_intelligence.py`: consultas naturais, provas e lembretes de prova;
- `exam_phrase_patch.py` / `exam_cancel_patch.py`: criação/cancelamento natural de prova;
- `attendance_patch.py`: base de faltas/presença explícita;
- `attendance_enhancement.py`: relatórios/limite e callback aprimorado;
- `attendance_management.py`: editar limite e excluir/corrigir falta;
- `attendance_production_fix.py`: T-10/T0, heartbeat e menu acadêmico final;
- `attendance_alarm.py`: contingência Durable Object para avisos acadêmicos.

Ao fim da Etapa 2 deve haver autoridade mais explícita, sem depender de uma pilha crescente de monkeypatches.

---

## 5. Contrato da importação que deve sobreviver

Fonte SIGAA recomendada:

```text
Componente Curricular | Local | Horário
```

Aceitar:

- PDF com texto pesquisável/selecionável;
- TXT.

Produção não depende de OCR.

O fluxo já possui uma decisão correta que deve permanecer:

```text
arquivo
→ parser
→ prévia
→ confirmação explícita
→ persistência
```

O que precisa mudar é a persistência: sair de `delete all + recreate` para plano de merge com identidade estável.

---

## 6. Próxima sequência da Etapa 2

```text
2.1 Inventário/autoridades
→ caracterização do parser e fluxos críticos

2.2 Identidade/modelo acadêmico
→ external_code / campos / política de arquivar-remover
→ identidade de sessão
→ associação estável de avaliações

2.3 Migration + backfill

2.4 Importador normalizado
→ adaptador SIGAA separado do modelo

2.5 Preview de diferenças
→ novo / alterado / mantido / removido

2.6 Merge confirmado
→ preservar IDs/histórico

2.7 Onboarding/documentação
```

---

## 7. Invariantes acadêmicos

- aula prevista nunca implica presença;
- `vou` não grava presença fictícia;
- falta só por ação explícita;
- reimportação não pode apagar histórico silenciosamente;
- importação sempre tem preview;
- imagem/scan não entra como PDF textual;
- dados isolados por usuário;
- provas não podem perder a associação com matéria silenciosamente.

---

## 8. Linguagem natural consolidada

A Etapa 1 deixou ativos:

- `language_primitives.py` — famílias/relações/referências/polaridade sem CRUD;
- `short_context.py` — contexto de 30 min, referências e listas posicionais;
- `correction_patch.py` — auto-reparo recente seguro;
- `compound_router.py` — mensagens compostas e lote confirmado;
- `temporal_language.py` — classifica alertas relativos/timers para a futura Etapa 3.

Quick timers não devem virar tarefas normais antes da Etapa 3.

---

## 9. Scheduler e performance

Scheduler possui redundância:

```text
Cron Trigger
+
Durable Objects (PersonalAlarm / AttendanceAlarm)
```

`notification_log` protege idempotência.

O caminho quente já recebeu cache por update, gates lexicais e reconciliação de alarms pós-resposta. Se latência voltar a ser problema, instrumentar por handler/D1/Telegram antes de otimizar novamente.

---

## 10. Banco e migrations

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
```

A lista anterior do handoff parava em `0008`; isso estava desatualizado e foi corrigido durante a 2.1.

Migration é fonte formal; `ensure_schema()` é defesa operacional, não substituto.

---

## 11. Validação

Fechamento técnico da Etapa 1:

- merge `f08bff2e4edf5303f8b79a5a420ecd80356043fa`;
- regressão pós-merge da `main`: success.

Handoff documental:

- merge `e3220d95aed43b1e5730709e56aa07d6716e77d9`.

Etapa 2.1 trabalha na branch `refactor/etapa-2-1-inventario-academico` e só deve ser mesclada após caracterização/regressão verde.

CI verde comprova regressão do repositório; não prova sozinho deploy Cloudflare.

---

## 12. Instrução para a próxima IA

1. confirmar commits posteriores;
2. ler `docs/ETAPA_2_1_INVENTARIO_ACADEMICO.md`;
3. fechar o gate 2.1 antes de alterar schema;
4. desenhar a **2.2 — identidade/modelo acadêmico** antes de migration;
5. não preservar o comportamento destrutivo da importação como requisito;
6. não religar NLU/Library histórica como atalho.

**Próximo trabalho oficial: fechar a Etapa 2.1 e desenhar a identidade acadêmica da 2.2.**
