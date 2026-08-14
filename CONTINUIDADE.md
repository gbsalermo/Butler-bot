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

O Butler **não executa OCR**. Tesseract, Pillow e `pytesseract` foram removidos das dependências.

Motivo: manter o projeto simples, portátil e mais adequado à futura hospedagem.

Se a pessoa só tiver uma imagem da grade, o Butler deve orientá-la a:

1. usar qualquer IA/ferramenta para converter a imagem em **PDF com texto pesquisável**;
2. enviar esse PDF ao Butler;
3. ou cadastrar as matérias uma por uma em `⚙️ Gerenciar matérias`.

PDF textual é extraído com `pypdf`.

### Lógica da importação

O parser procura códigos SIGAA como `35M45`, `24M23`, `3T23`, usa `src/sigaa_schedule.py` e tenta identificar matéria, local/sala, código e sessões resultantes.

Antes de gravar, o Butler mostra uma prévia obrigatória. Somente `✅ Importar grade` persiste os dados.

Se a matéria já existir, `upsert_subject_schedule()` substitui os horários e reativa a matéria.

A confirmação continua obrigatória porque o próprio documento/SIGAA pode conter informação incorreta.

## ⏰ Normalização dos horários SIGAA

O Butler usa **horas completas** como representação oficial dos blocos acadêmicos.

Exemplos:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

`src/sigaa_schedule.py` é a fonte da conversão para cadastro por código e importação.

`init_database()` também normaliza registros antigos que ainda usam minutos quebrados do SIGAA, como `08:01–09:40` e `10:00–11:40`.

O horário manual continua tendo prioridade quando o usuário corrige uma informação, como no Laboratório de Sistemas Digitais I.

## 🕴️ Personality Engine v1

Arquivos principais:

- `src/personality.py`;
- `src/context_engine.py`;
- `src/casual_handlers.py`;
- `src/personality_navigation.py`;
- `src/scheduler.py`.

Personalidade: competente, informal, levemente cansado/cínico e útil. Pode provocar a situação/comportamento, nunca humilhar o usuário.

Tons: `NEUTRO`, `LEVE`, `SARCASTICO`, `CUIDADOSO`.

Day-off e situações sensíveis permanecem sem sarcasmo.

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

- adicionar/listar/concluir/editar/remover;
- data, horário, detalhes e antecedência configuráveis;
- lembretes proativos;
- concluir ou adiar no próprio aviso;
- cancelamento visível durante fluxos.

### 🏠 Cotidiano

- lista persistente do que falta em casa;
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

1. validar importação usando um PDF textual real do tipo `grade_curricular.pdf`;
2. validar onboarding/nome preferido nas duas versões;
3. validar que `main_generic` nasce sem grade e sem Protocol Mass;
4. retomar resumo diário + personalidade contextual baseada em comportamento;
5. streaks de metas/rotinas;
6. permitir corrigir/apagar série de treino registrada por engano;
7. finanças persistentes;
8. integração com ônibus;
9. consolidar testes e hospedagem 24/7 posteriormente.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo com o estado real;
2. atualizar README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
