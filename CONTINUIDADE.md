# Continuidade do desenvolvimento — Butler

> Este documento registra **decisões duradouras**. Ele não repete o estado técnico completo nem o roadmap detalhado.
>
> - runtime atual: `docs/ARCHITECTURE.md`;
> - visão completa: `docs/BUTLER_DOSSIE_MESTRE.md`;
> - ordem oficial de evolução: `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`;
> - classificação estrutural: `docs/INVENTARIO_ETAPA_0.md`.

---

## 1. Objetivo permanente

Butler é um assistente pessoal via Telegram. A experiência desejada combina organização cotidiana, estudo, universidade, projetos, trabalho, hábitos e interesses sem virar apenas CRUD/menu nem uma IA que decide silenciosamente pelo usuário.

Princípios permanentes:

1. operações críticas são determinísticas;
2. ação explícita vence contexto antigo;
3. não inventar presença, conclusão, gasto, compromisso, treino, progresso ou memória;
4. dados e estado são isolados por usuário;
5. escrita ambígua exige confirmação quando há risco;
6. botões e linguagem natural coexistem;
7. contexto auxilia, mas não sequestra mudança de assunto;
8. comportamento novo exige regressão;
9. nova funcionalidade deve entrar no módulo autoritativo sempre que possível;
10. documentação deve separar claramente ativo, legado e preservado.

---

## 2. Runtime oficial

Produção:

```text
Telegram Webhook
→ Cloudflare Python Worker
→ D1 / Durable Objects
→ Telegram Bot API
```

Entrypoints:

```text
cloudflare/src/worker.py
cloudflare/src/entry.py
```

A raiz `src/` continua preservada como runtime histórico polling/SQLite e não governa produção.

---

## 3. Decisão arquitetural atual

Uma geração anterior tentou centralizar linguagem/contexto em:

```text
context_router.py
intent_parser.py
action_policy.py
context_memory.py
suggestion_engine.py
Butler Library
```

Esse trabalho foi preservado, mas **não é o roteador central do webhook atual**.

A produção privilegia:

- handlers explícitos e ordenados;
- fast paths conservadores;
- estados guiados;
- módulos autoritativos por domínio;
- contexto operacional curto;
- fallback estreito.

Reativação de qualquer camada preservada precisa definir antes:

- posição no dispatcher;
- precedência contra o Core;
- política de escrita;
- isolamento por usuário;
- regressão de fluxo real;
- flags coerentes no `/health`.

---

## 4. Resultado duradouro da Etapa 0

A fase “arrumar a casa” estabelece as seguintes regras daqui para frente:

### Dispatcher

`entry.py` é a autoridade da precedência e expõe funções testáveis para mensagens, callbacks e cron.

### Menu

`operational_menu.py` é a autoridade do menu principal. Outros módulos podem manter submenus próprios, mas não uma segunda definição concorrente do menu principal.

### Lembretes

`reliable_reminders.py` é a autoridade temporal para `daily_items`.

A antiga cadeia duplicada em `quality_patch.py`/`conversation_layer.py` foi removida e `reminder_policy.py` deixou de existir.

### Schema

`cloudflare/migrations/` é a fonte formal de evolução D1. `ensure_schema()` é apenas tolerância operacional.

Na Etapa 0, Ler/Ver Depois passou a possuir migration formal (`0008_later_items.sql`).

### Exclusão de código

Não apagar por nome, idade ou aparência. Antes de excluir, classificar e demonstrar que o runtime não depende do componente. A Etapa 0 removeu apenas código com desuso comprovado.

---

## 5. Contexto, linguagem e memória

Contexto operacional ativo usa principalmente:

```text
natural_events
user_sessions
conversation_layer.py
reference_patch.py
task_context_patch.py
```

A NLU ampla, memória pessoal genérica, sugestões transversais e Library genérica continuam desabilitadas no roteamento principal.

A próxima frente oficial é **Linguagem natural + estabilidade de conversa**. Ela deve melhorar português real — conjugações, conjunções, frases compostas, elipses, referências e correções — sem religar cegamente toda a arquitetura histórica.

---

## 6. Política conversa × ação

A direção conceitual permanece:

```text
comentário → conversa
pedido explícito → ação validada pelo Core
problema → ajuda/sugestão quando apropriado
ambiguidade → confirmação
```

A implementação atual é distribuída por handlers, não por `action_policy.py` global.

Exceção consciente: frases domésticas claras como `acabou o café` atualmente atualizam diretamente a lista de itens faltando. Mudar isso é decisão funcional separada e deve ter regressão própria.

---

## 7. Scheduler e entrega

Princípios permanentes:

- não enviar aviso obsoleto muito depois do horário;
- registrar envio crítico como concluído somente quando a entrega tiver confirmação adequada;
- `notification_log` protege idempotência;
- falha de um subsistema não derruba os demais;
- callbacks repetidos não podem repetir efeito crítico;
- Day-off deve ser respeitado conforme a política de cada categoria.

Cron operacional:

```text
day_off
→ attendance
→ daily_items
→ routines
→ summaries
→ legado/compatibilidade
```

---

## 8. Acadêmico

Aulas são previstas; presença nunca é presumida.

O sistema pode avisar, perguntar e registrar resposta explícita, além de calcular limites de faltas conforme configuração.

A Etapa 2 do roadmap deve:

- consolidar a família acadêmica/presença;
- concluir edição completa de matérias;
- suportar múltiplos horários/localizações;
- transformar importação SIGAA em um adaptador sobre modelo acadêmico normalizado;
- preparar reaproveitamento do motor de importação para cursos.

---

## 9. Musculação

O perfil proprietário preserva o Protocol Mass de 12 semanas; usuários genéricos podem possuir ficha própria.

Regras permanentes:

- não aplicar protocolo pessoal a outro usuário;
- registrar carga/repetição somente quando informadas;
- substituição não apaga histórico;
- evolução usa dados realmente registrados.

---

## 10. Cursos e trilhas

Cursos são parte oficial do roadmap, não funcionalidade ativa ainda.

Modelo conceitual:

```text
Curso
→ módulo
   → conteúdo/submódulo
      → materiais/atividades
      → progresso
```

Decisões já tomadas:

- curso autogerido mantém o próximo conteúdo pendente até conclusão/pulo explícito;
- curso ao vivo segue calendário fixo e não desloca aula automaticamente;
- conclusão é explícita;
- importador deve agrupar mídias, listas, soluções, revisões e materiais relacionados antes de salvar;
- baixa confiança exige prévia/confirmação.

Detalhes completos estão na Trilha Definitiva.

---

## 11. Projetos, Inbox e priorização

Também são compromissos do roadmap oficial:

- Caixa de entrada para captura rápida sem classificação imediata;
- Projetos/Trabalho com estado, próximos passos, bloqueios e “onde parei?”;
- Priorização do dia/semana baseada em regras explicáveis e dados reais;
- integração posterior com cursos, agenda, clima, rotinas e pendências.

Não implementar essas frentes antes dos gates definidos na Trilha.

---

## 12. Library e conhecimento

Os acervos de culinária, jogos, cultura pop, livros e filosofia continuam preservados.

Direção permanente:

- preferir dados, aliases, tags e índice, não um `if` por exemplo;
- Library pode sugerir, mas ação persistente pertence ao Core;
- direitos autorais: preferir dados abertos, domínio público, documentos próprios e resumos/metadados.

Reativação seletiva pertence à Etapa 7.

---

## 13. Multiusuário e proprietário

Toda persistência pessoal é isolada por usuário.

A barreira `is_owner(chat_id)` não deve ser removida sem mecanismo equivalente.

Recursos administrativos permanecem exclusivos do proprietário. Seeds/configurações pessoais devem migrar para configuração privada antes de distribuição mais ampla.

---

## 14. Banco e migrations

Disciplina obrigatória:

1. migration versionada;
2. backfill explícito quando necessário;
3. índice quando a consulta justificar;
4. `ensure_schema()` apenas quando houver motivo operacional;
5. teste;
6. documentação.

Migration destrutiva exige snapshot/export D1 e plano de rollback.

Defaults retroativos não devem depender apenas de `app.ensure_user()` porque usuários existentes podem não passar pelo bootstrap completo.

---

## 15. Patches e dívida técnica

A estratégia de patches permitiu evoluir sem reescrever o Core, mas não deve continuar crescendo indefinidamente.

Regra:

```text
não criar *_fix2.py, *_final.py ou nova camada paralela
sem justificar por que o módulo autoritativo não pode receber a mudança
```

Quando um domínio for trabalhado e houver cobertura suficiente, consolidar a regra no módulo dono e remover compatibilidade antiga em PR próprio ou na etapa funcional correspondente.

---

## 16. Testes

A suíte em `cloudflare/tests/` deve proteger funções determinísticas e o caminho realmente alcançado pelo dispatcher.

Prioridades:

- sequências completas de conversa;
- falsos positivos;
- dois usuários;
- callbacks repetidos;
- scheduler/idempotência;
- cancelamento/voltar;
- precedência de handlers.

CI verde é condição necessária para merge, mas não prova deploy Cloudflare.

---

## 17. Ordem oficial de evolução

A partir da Etapa 0 concluída:

```text
1. 🗣️ Linguagem natural + conversa real
2. 🎓 Acadêmico + importação
3. 📚 Cursos e trilhas
4. 📥 Caixa de entrada
5. 🗂️ Projetos e trabalho
6. 🧭 Resumo e priorização
7. 🧠 Memória + Library seletiva
8. 🔒 Hardening
```

A fonte detalhada e os critérios de saída de cada fase estão em `docs/TRILHA_DESENVOLVIMENTO_DEFINITIVA.md`.

---

## 18. Regra de atualização documental

Ao mudar:

- **runtime/autoridade:** atualizar `docs/ARCHITECTURE.md` e o Dossiê quando material;
- **roadmap/ordem futura:** atualizar a Trilha Definitiva;
- **decisão duradoura:** atualizar este arquivo;
- **classificação estrutural:** atualizar Inventário;
- **capacidade pública/uso:** atualizar README.

Não duplicar detalhes por conveniência. Cada documento tem uma função clara.
