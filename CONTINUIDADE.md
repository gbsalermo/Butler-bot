# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite, `python-dotenv` e `pypdf`.
- Execução local via polling.
- Bot pessoal: `Butler` / `@ButlerSal_BOT`.
- Prioridade continua sendo funcionalidade e experiência de uso antes de suíte de testes.

## Filosofia

O Butler deve parecer um assistente presente, não um conjunto de formulários. A tela inicial prioriza ações rápidas e recorrentes; módulos menos urgentes ficam em `🏠 Cotidiano`.

## 👥 Multiusuário por chat_id — etapa 0 concluída

Decisão estrutural: a versão genérica é um único Butler para poucas pessoas, mas cada `chat_id` deve ter experiência e dados completamente isolados.

Novo arquivo: `src/user_scope.py`.

### Rolling local

Na versão genérica (`python -m src.main_generic`):

- `BUTLER_MULTIUSER=1` é ativado automaticamente;
- todo update passa primeiro por `register_user_scope()`;
- mensagens e callbacks definem o `chat_id` atual antes de qualquer regra de negócio;
- cada chat recebe um SQLite próprio em `data/butler_generic_users/<chat_id>.db`;
- existe um pequeno registro central `data/butler_generic_registry.db` apenas para o scheduler saber quais chats existem;
- as tabelas do usuário são inicializadas automaticamente na primeira interação do processo.

Isso isola sem reescrever toda a regra de negócio:

- usuários/nome preferido;
- matérias e horários;
- tarefas/compromissos;
- lista de mercado;
- metas;
- rotinas e logs;
- musculação manual da versão genérica;
- Day-off.

### Scheduler multiusuário

`src/scheduler.py` agora:

1. obtém os chats registrados;
2. seleciona o armazenamento daquele `chat_id`;
3. verifica o Day-off somente daquele chat;
4. lê aulas, tarefas e rotinas somente daquele chat;
5. envia o lembrete exclusivamente para ele;
6. inclui `chat_id` nas chaves internas de deduplicação.

Nunca voltar ao modelo de ler um evento global e dispará-lo para todos os chats.

### Butler pessoal

`python -m src.main` continua usando `data/butler.db` como antes e mantém:

- grade pessoal;
- correção manual do Laboratório de Sistemas Digitais I em segunda 14:00–16:00;
- Protocol Mass de 12 semanas;
- histórico pessoal existente.

O Protocol Mass continua exclusivo do Butler pessoal nesta etapa.

### Cloudflare

O isolamento por `chat_id` é regra de domínio e deve permanecer na hospedagem. O SQLite por arquivo é somente a implementação rolling local.

Na migração Cloudflare, trocar a implementação de persistência por D1/armazenamento persistente, preservando a ideia de tenant por `chat_id`. Não depender do filesystem do Worker como armazenamento definitivo.

## ⚡ Menu principal orientado a ação

`src/ui_layout.py` centraliza os teclados.

Menu principal atual:

- `🌙 Day-off`
- `➕ Adicionar`
- `🗓️ Hoje`
- `🛒 Item faltando`
- `📚 Matérias`
- `🏠 Cotidiano`
- `🏋️ Musculação`

`➕ Adicionar` abre somente:

- `✅ Nova tarefa`
- `📅 Novo compromisso`

Tarefas e compromissos ficam em Cotidiano para gerenciamento completo.

### Cotidiano

- `✅ Tarefas`
- `📅 Compromissos`
- `🛒 O que está faltando?`
- `➕ Item faltando`
- `🎯 Metas`
- `🧘 Rotinas`
- `💰 Finanças`
- `👤 Como me chamar`
- retorno ao menu principal

Novo arquivo: `src/quick_access.py`.

## 📌 Pendência não é mais um tipo

`pendencia` deixou de ser uma categoria criada pelo usuário.

Agora:

- tarefa = algo que precisa ser feito;
- compromisso = evento/agendamento;
- pendência = tarefa com data vencida e ainda não concluída.

`init_daily_store()` migra registros antigos com `kind = 'pendencia'` para `kind = 'tarefa'`.

## 🗓️ Hoje

`src/assistant_views.py` reúne:

- aulas do dia;
- tarefas do dia;
- compromissos do dia;
- bloco `📌 Pendências — tarefas vencidas`;
- musculação manual do dia quando cadastrada;
- quantidade de itens faltando em casa.

## ⚡ Captura rápida

`src/quick_capture.py` reduz passos em ações simples.

### Tarefa/compromisso

Fluxo:

1. título;
2. `Hoje`, `Outro dia` ou `Sem data`;
3. horário quando houver data;
4. salva.

Não pergunta observação nem antecedência por padrão. Lembrete do fluxo rápido = na hora marcada (`0` minutos).

Validações:

- não aceitar data passada;
- se for hoje, não aceitar horário passado ou igual ao momento atual;
- timezone: `BUTLER_TIMEZONE`.

### Item faltando

Aceita:

- `sal`;
- `sal, açúcar, café`;
- `falta sal, açúcar, café`;
- `café | 2 pacotes` para quantidade opcional.

## 👤 Nome preferido

`src/onboarding.py` controla `/start`.

- registra `chat_id`;
- pergunta `preferred_name` quando necessário;
- pode ser alterado em `🏠 Cotidiano → 👤 Como me chamar`;
- respostas casuais e lembretes usam o nome preferido quando possível.

Na versão genérica, esse registro vive dentro do armazenamento isolado daquele chat.

## 📥 Importação da grade

Opção:

`📚 Matérias → 📥 Importar grade por PDF/texto`

Aceitos:

- PDF com texto pesquisável;
- `.txt`.

Não aceitos:

- imagem/foto/screenshot;
- PDF escaneado sem camada de texto.

Sem OCR/Tesseract. Se a pessoa só tiver imagem, o Butler orienta converter em IA/ferramenta para PDF com texto pesquisável ou cadastrar manualmente.

O parser procura códigos SIGAA (`35M45`, `24M23`, `3T23` etc.) e sempre mostra prévia antes de persistir.

## ⏰ Horários SIGAA

Representação oficial por horas completas:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

Correções manuais do usuário têm prioridade.

## 🕴️ Personality Engine

Arquivos principais:

- `src/personality.py`;
- `src/context_engine.py`;
- `src/casual_handlers.py`;
- `src/personality_navigation.py`;
- `src/scheduler.py`.

Personalidade: competente, informal, levemente cansada/cínica e útil. Pode provocar a situação, nunca humilhar o usuário. Day-off e situações sensíveis ficam sem sarcasmo.

## 🏋️ Protocol Mass — somente Butler pessoal

- 12 semanas;
- início único por `🚀 Começar os trabalhos`;
- treino do dia;
- falta com motivo;
- substitutos oficiais;
- registro série por série;
- carga/repetições;
- histórico;
- progresso semanal;
- reinício temporário para testes.

## Próxima sequência funcional

Com a etapa 0 de isolamento pronta, retomar:

1. personalidade baseada em comportamento real por usuário;
2. resumo diário automático individual;
3. resumo noturno/semanal individual;
4. metas com streak real por usuário;
5. finanças persistentes;
6. linguagem natural para criar/alterar ações.

## Próximos testes

1. testar o Butler pessoal e confirmar que os dados antigos permanecem intactos;
2. iniciar `src.main_generic` com um chat A e cadastrar uma tarefa/item/matéria;
3. abrir o mesmo bot em um chat B e confirmar que nasce vazio;
4. ativar Day-off em A e confirmar que B continua normal;
5. criar lembretes em A e B e conferir destinatários;
6. testar callbacks `Concluir` / `+10 min` nos dois chats;
7. só depois avançar para personalidade comportamental.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo;
2. atualizar README quando o fluxo público mudar significativamente;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
