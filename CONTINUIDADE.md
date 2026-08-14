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

Existe **um único código-base com dois entrypoints**.

### Butler pessoal

`python -m src.main`

- banco `data/butler.db`;
- mantém a grade pessoal já cadastrada;
- mantém a correção manual de Laboratório de Sistemas Digitais I (segunda 14:00–16:00);
- mantém o Protocol Mass de 12 semanas e histórico de treino.

### Butler genérico

`python -m src.main_generic`

- usa `.env.generic`;
- token Telegram próprio;
- banco separado `data/butler_generic.db` por padrão;
- não chama `seed_default_schedule()`;
- não inicializa/expõe Protocol Mass;
- não contém grade ou treino pessoal;
- `/start` registra o `chat_id` e pergunta como a pessoa quer ser chamada;
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

## 📥 Importação de grade por PDF/imagem

Arquivos:

- `src/schedule_importer.py`;
- `src/schedule_import_handlers.py`.

Opção:

`📚 Matérias → 📥 Importar grade por PDF/imagem`

Formatos:

- PDF com texto: PyMuPDF;
- PDF escaneado: renderização + OCR;
- JPG/PNG/WebP/foto: OCR via `pytesseract` + Pillow.

`pytesseract` exige o executável Tesseract OCR instalado no sistema para imagens/PDFs escaneados.

### Lógica da importação

O parser procura códigos SIGAA como `35M45`, `24M23`, `3T23`, usa `src/sigaa_schedule.py` e tenta identificar matéria, local/sala, código e sessões resultantes.

Antes de gravar, o Butler mostra uma **prévia obrigatória**. Somente `✅ Importar grade` persiste os dados.

Se a matéria já existir, `upsert_subject_schedule()` substitui os horários daquela matéria e a reativa.

A confirmação é obrigatória porque OCR e o próprio SIGAA podem conter informação errada.

## ⏰ Normalização dos horários SIGAA

Decisão atual: o Butler usa **horas completas** como representação oficial dos blocos acadêmicos, em vez dos minutos quebrados exibidos pelo SIGAA.

Exemplos:

- `M23` → `08:00–10:00`;
- `M45` → `10:00–12:00`;
- `T23` → `14:00–16:00`;
- `T2345` → `14:00–18:00`;
- `N12` → `18:00–20:00`.

Essa normalização acontece diretamente em `src/sigaa_schedule.py`, portanto vale tanto para cadastro por código quanto para importação por PDF/imagem.

O horário manual continua tendo prioridade quando o usuário corrige uma informação do SIGAA, como no caso do Laboratório de Sistemas Digitais I.

## 🕴️ Personality Engine v1

Arquivos:

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
- `📥 Importar grade por PDF/imagem`;
- retorno ao menu principal.

## Funcionalidades consolidadas

### 🌙 Day-off

- estado persistente;
- silencia o scheduler;
- permanece após reinício;
- retorno por frases como `Butler, preciso de você!` e `Chamar, Butler!`.

### 📚 Acadêmico

- grade persistente;
- tradução de códigos SIGAA em horas completas;
- adicionar/remover/trancar/editar matérias;
- importação por PDF/imagem com confirmação;
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
- falta com motivo (`😕 Não consegui treinar hoje`);
- substitutos oficiais;
- registro série por série;
- carga e repetições por série;
- histórico de carga;
- progresso semanal;
- `🔄 Reiniciar os trabalhos` ainda temporário para testes.

A versão genérica não registra os módulos Protocol Mass e começa com musculação manual vazia.

## Scheduler

Trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. Lembretes passam pelo Personality Engine e usam `preferred_name` quando cadastrado.

## Finanças

Continua planejado, ainda sem persistência real.

## Próximos passos sugeridos

1. validar importação de grade com screenshot/PDF real no Telegram;
2. validar onboarding/nome preferido nas duas versões;
3. validar que `main_generic` nasce realmente sem grade e sem Protocol Mass;
4. retomar resumo diário + personalidade contextual baseada em comportamento;
5. streaks de metas/rotinas;
6. permitir corrigir/apagar série de treino registrada por engano;
7. finanças persistentes;
8. integração com ônibus;
9. consolidar testes e hospedagem 24/7 posteriormente.

## Regra de continuidade

Ao concluir nova etapa:

1. atualizar este arquivo com o estado real;
2. atualizar o README quando funcionalidades ou execução mudarem;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
