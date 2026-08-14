# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento concentrado na `main`.
- Stack: Python, `python-telegram-bot[job-queue]`, SQLite e `python-dotenv`.
- Execução local via polling.
- Nome do bot pessoal: `Butler`.
- Username pessoal atual: `@ButlerSal_BOT`.
- Prioridade continua sendo funcionalidade antes de suíte de testes.

## Filosofia do produto

O Butler deve parecer um assistente presente, não um formulário. Deve reduzir carga mental, lembrar antes que o usuário precise conferir, guardar pequenas informações persistentes, conversar de forma natural e respeitar períodos de descanso sem cobrança.

## ⚡ Captura rápida

Criado `src/quick_capture.py` para reduzir atrito em ações simples e recorrentes.

### Tarefas, compromissos e pendências

Fluxo novo de criação:

1. clicar em adicionar;
2. informar somente o título;
3. escolher `Hoje`, `Outro dia` ou `Sem data`;
4. se houver data, informar o horário;
5. salvar imediatamente.

Não perguntar por padrão observação nem antecedência. O lembrete padrão dos itens criados pelo fluxo rápido é `0` minutos, ou seja, na hora marcada.

Validações:

- não aceitar data anterior ao dia atual;
- para hoje, não aceitar horário anterior ou igual ao momento atual;
- para data futura, aceitar qualquer horário válido;
- timezone usado: `BUTLER_TIMEZONE`.

Os fluxos antigos de listar, concluir, editar e remover permanecem disponíveis.

### Lista do que falta em casa

`➕ Item faltando` agora deve ser instantâneo.

Aceita:

- `sal` → salva um item;
- `sal, açúcar, café` → salva três itens;
- `falta sal, açúcar, café` → remove o prefixo e salva três itens;
- `café | 2 pacotes` → quantidade opcional no mesmo envio.

Não perguntar quantidade nem observação em mensagens separadas.

O módulo é registrado antes dos handlers antigos no mesmo group, assumindo apenas os fluxos rápidos e preservando as demais operações existentes.

## 🧩 Dois modos de execução

Existe um único código-base com dois entrypoints.

### Butler pessoal

`python -m src.main`

- banco `data/butler.db`;
- mantém a grade pessoal;
- mantém a correção manual de Laboratório de Sistemas Digitais I em segunda 14:00–16:00;
- mantém Protocol Mass de 12 semanas e histórico de treino.

### Butler genérico

`python -m src.main_generic`

- usa `.env.generic`;
- token Telegram próprio;
- banco separado `data/butler_generic.db` por padrão;
- não chama `seed_default_schedule()`;
- não inicializa/expõe Protocol Mass;
- não contém grade ou treino pessoal;
- `/start` registra `chat_id` e pergunta como a pessoa quer ser chamada;
- musculação começa vazia.

## 👤 Nome preferido / onboarding

`src/onboarding.py` controla `/start`.

A tabela `users` possui `preferred_name`.

Fluxo:

1. registra/atualiza `chat_id`, Telegram user id, nome e username;
2. se não existir `preferred_name`, pergunta como a pessoa quer ser chamada;
3. salva o nome/apelido;
4. abre o menu principal;
5. pode ser alterado em `🏠 Cotidiano → 👤 Como me chamar`.

Respostas casuais e lembretes proativos usam o nome preferido quando possível.

## 📥 Importação de grade — decisão simplificada

Arquivos:

- `src/schedule_importer.py`;
- `src/schedule_import_handlers.py`.

Opção atual:

`📚 Matérias → 📥 Importar grade por PDF/texto`

### Formatos aceitos

- PDF com texto pesquisável/selecionável;
- arquivo `.txt`.

### Formatos não aceitos

- imagem/foto;
- JPG/PNG/WebP;
- screenshot;
- PDF escaneado que contenha apenas imagem.

O Butler não executa OCR. Se a pessoa só tiver uma imagem, deve ser orientada a usar qualquer IA/ferramenta para converter para PDF com texto pesquisável ou cadastrar manualmente.

PDF textual é extraído com `pypdf`.

O parser procura códigos SIGAA como `35M45`, `24M23`, `3T23`, usa `src/sigaa_schedule.py` e apresenta prévia obrigatória antes de persistir.

## ⏰ Normalização dos horários SIGAA

O Butler usa horas completas como representação oficial:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

O horário manual continua tendo prioridade quando o usuário corrige uma informação, como no Laboratório de Sistemas Digitais I.

## 🕴️ Personality Engine v1

Arquivos principais:

- `src/personality.py`;
- `src/context_engine.py`;
- `src/casual_handlers.py`;
- `src/personality_navigation.py`;
- `src/scheduler.py`.

Personalidade: competente, informal, levemente cansado/cínico e útil. Pode provocar a situação/comportamento, nunca humilhar o usuário. Day-off e situações sensíveis permanecem sem sarcasmo.

## 🧭 Organização dos menus

`src/ui_layout.py` centraliza os teclados.

### Menu principal

- `🌙 Day-off`
- `🏋️ Musculação`
- `📚 Matérias`
- `✅ Tarefas`
- `📅 Compromissos`
- `📌 Pendências`
- `🗓️ Hoje`
- `🏠 Cotidiano`

### Cotidiano

- lista do que está faltando;
- metas;
- rotinas/autocuidado;
- finanças;
- `👤 Como me chamar`;
- retorno ao menu principal.

### Acadêmico

- `📚 Minhas matérias`;
- `⚙️ Gerenciar matérias`;
- `📥 Importar grade por PDF/texto`;
- retorno ao menu principal.

## Funcionalidades consolidadas

### 🌙 Day-off

- estado persistente;
- silencia scheduler;
- permanece após reinício;
- retorno por `Butler, preciso de você!` e variações.

### 📚 Acadêmico

- grade persistente;
- tradução SIGAA em horas completas;
- adicionar/remover/trancar/editar matérias;
- importação de PDF textual/`.txt` com confirmação;
- matérias trancadas não geram lembretes.

### ✅ Tarefas, 📅 compromissos e 📌 pendências

- criação rápida;
- listar/concluir/editar/remover;
- data e horário opcionais;
- lembretes proativos;
- concluir ou adiar no próprio aviso;
- cancelamento visível durante fluxos.

### 🏠 Cotidiano

- lista persistente do que falta em casa com captura rápida;
- metas gerais e progresso;
- rotinas/autocuidado;
- finanças ainda como módulo futuro;
- visão `🗓️ Hoje`.

## 🏋️ Musculação — Protocol Mass (somente Butler pessoal)

- 12 semanas carregadas;
- `🚀 Começar os trabalhos` inicia o protocolo inteiro apenas uma vez;
- treino do dia;
- falta com motivo;
- substitutos oficiais;
- registro série por série;
- carga e repetições por série;
- histórico de carga;
- progresso semanal;
- `🔄 Reiniciar os trabalhos` temporário para testes.

A versão genérica não registra Protocol Mass e começa com musculação manual vazia.

## Scheduler

Trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. Lembretes passam pelo Personality Engine e usam `preferred_name` quando cadastrado.

## Finanças

Continua planejado, ainda sem persistência real.

## Próximos passos sugeridos

1. validar captura rápida de tarefa para hoje em poucos minutos;
2. validar rejeição de data/horário passado;
3. validar captura múltipla de itens de mercado;
4. validar importação de grade e versão genérica;
5. retomar resumo diário + personalidade contextual baseada em comportamento;
6. streaks de metas/rotinas;
7. finanças persistentes;
8. integração com ônibus;
9. consolidar testes e hospedagem posteriormente.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo com o estado real;
2. atualizar README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
