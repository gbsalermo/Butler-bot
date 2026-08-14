# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite, `python-dotenv` e `pypdf`.
- Execução local via polling.
- Bot pessoal: `Butler` / `@ButlerSal_BOT`.
- Prioridade continua sendo funcionalidade e experiência de uso antes de suíte de testes.

## Filosofia

O Butler deve parecer um assistente presente, não um conjunto de formulários. A tela inicial deve priorizar ações rápidas e recorrentes; módulos menos urgentes ficam em `🏠 Cotidiano`.

## ⚡ Menu principal orientado a ação

`src/ui_layout.py` centraliza os teclados.

Menu principal atual:

- `🌙 Day-off`
- `➕ Adicionar`
- `🗓️ Hoje`
- `🛒 Item faltando`
- `🏋️ Musculação`
- `📚 Matérias`
- `🏠 Cotidiano`

`➕ Adicionar` abre somente:

- `✅ Nova tarefa`
- `📅 Novo compromisso`

Tarefas e compromissos deixaram o menu principal e passaram para Cotidiano.

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

Decisão estrutural: `pendencia` deixou de ser uma categoria que o usuário cria.

Agora:

- tarefa = algo que precisa ser feito;
- compromisso = evento/agendamento;
- pendência = tarefa com data vencida e ainda não concluída.

`init_daily_store()` migra registros antigos com `kind = 'pendencia'` para `kind = 'tarefa'`.

Botões antigos de Pendências, caso ainda apareçam num teclado antigo do Telegram, apenas explicam a nova regra e direcionam para `➕ Adicionar` / `🗓️ Hoje`.

## 🗓️ Hoje

`src/assistant_views.py` reúne:

- aulas do dia;
- tarefas do dia;
- compromissos do dia;
- bloco `📌 Pendências — tarefas vencidas`;
- musculação manual do dia quando cadastrada;
- quantidade de itens faltando em casa.

Pendências são calculadas automaticamente a partir de tarefas vencidas.

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

Depois de salvar, volta para o menu principal.

### Item faltando

Aceita:

- `sal`;
- `sal, açúcar, café`;
- `falta sal, açúcar, café`;
- `café | 2 pacotes` para quantidade opcional.

Depois de salvar, volta para o menu principal.

## 🧩 Dois modos de execução

### Butler pessoal

`python -m src.main`

- banco `data/butler.db`;
- grade pessoal;
- correção manual do Laboratório de Sistemas Digitais I em segunda 14:00–16:00;
- Protocol Mass de 12 semanas e histórico de treino.

### Butler genérico

`python -m src.main_generic`

- `.env.generic`;
- token próprio;
- banco `data/butler_generic.db`;
- sem grade pessoal;
- sem Protocol Mass;
- pergunta no `/start` como a pessoa quer ser chamada;
- musculação começa vazia.

## 👤 Nome preferido

`src/onboarding.py` controla `/start`.

- registra `chat_id`;
- pergunta `preferred_name` quando necessário;
- pode ser alterado em `🏠 Cotidiano → 👤 Como me chamar`;
- respostas casuais e lembretes usam o nome preferido quando possível.

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

## Próximos testes

1. `/menu` e conferir o novo painel de acesso rápido;
2. `➕ Adicionar → Nova tarefa` para alguns minutos à frente;
3. tentar horário passado e confirmar bloqueio;
4. `🛒 Item faltando` com um e vários itens;
5. deixar uma tarefa vencer e confirmar que aparece como `📌 Pendência` em `🗓️ Hoje`;
6. validar versão genérica e importação da grade;
7. depois retomar resumo diário + personalidade comportamental.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo;
2. atualizar README quando o fluxo público mudar significativamente;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
