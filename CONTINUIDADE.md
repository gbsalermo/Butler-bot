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

A partir desta etapa existe **um único código-base com dois entrypoints**. Não criar fork separado enquanto não houver necessidade real.

### Butler pessoal

Entry point:

`python -m src.main`

Características:

- usa o banco pessoal padrão `data/butler.db`;
- mantém a grade acadêmica já cadastrada;
- mantém a correção manual de Laboratório de Sistemas Digitais I (segunda 14:00–16:00);
- mantém o Protocol Mass de 12 semanas e histórico de treino;
- continua sendo a versão principal de desenvolvimento.

### Butler genérico

Entry point:

`python -m src.main_generic`

Configuração:

- `.env.generic`, criado a partir de `.env.generic.example`;
- token Telegram próprio;
- banco separado `data/butler_generic.db` por padrão.

Regras:

- não chama `seed_default_schedule()`;
- não inicializa/expõe Protocol Mass;
- não contém grade ou treino pessoal;
- `/start` registra o `chat_id` da pessoa;
- pergunta como ela quer ser chamada;
- musculação começa vazia e usa o cadastro manual disponível no código-base;
- tarefas, compromissos, pendências, Day-off, metas, rotinas, lista de mercado, personalidade e scheduler continuam disponíveis.

A separação por banco/token impede que os dados pessoais do Butler principal sejam enviados para a outra instância.

## 👤 Nome preferido / onboarding

Novo arquivo: `src/onboarding.py`.

A tabela `users` ganhou `preferred_name` por migração compatível com bancos existentes.

Fluxo:

1. `/start` registra/atualiza `chat_id`, Telegram user id, nome e username;
2. se não existir `preferred_name`, pergunta como a pessoa quer ser chamada;
3. salva o nome/apelido;
4. abre o menu principal;
5. o valor pode ser alterado depois em `🏠 Cotidiano → 👤 Como me chamar`.

O `/start` antigo foi removido de `home_menu.py`; onboarding agora é o único dono desse comando.

Respostas casuais e lembretes proativos já substituem `chefe` pelo nome preferido quando possível.

## 📥 Importação de grade por PDF/imagem

Novos arquivos:

- `src/schedule_importer.py` — extração e interpretação;
- `src/schedule_import_handlers.py` — fluxo Telegram com prévia/confirmação.

A opção aparece em:

`📚 Matérias → 📥 Importar grade por PDF/imagem`

Formatos:

- PDF com texto: PyMuPDF;
- PDF escaneado: renderização + OCR;
- JPG/PNG/WebP/foto: OCR via `pytesseract` + Pillow.

Dependências adicionadas ao `requirements.txt`:

- `PyMuPDF`;
- `Pillow`;
- `pytesseract`.

Observação operacional: `pytesseract` exige que o executável **Tesseract OCR** esteja instalado no sistema para imagens/PDFs escaneados.

### Lógica da importação

O parser procura códigos SIGAA como:

- `35M45`;
- `24M23`;
- `3T23`.

Usa `src/sigaa_schedule.py` para transformar os códigos em dias e horários.

A importação tenta identificar:

- nome da matéria;
- local/sala;
- código SIGAA;
- sessões resultantes.

Antes de gravar, o Butler mostra uma **prévia obrigatória**. Somente `✅ Importar grade` persiste os dados.

Se a matéria já existir, `upsert_subject_schedule()` substitui os horários daquela matéria e a reativa. Não cria duplicata.

A confirmação é importante porque OCR e o próprio SIGAA podem estar errados. Não remover essa etapa. O caso do laboratório pessoal demonstra por que um horário manual pode ser mais correto que o código exibido.

## 🕴️ Personality Engine v1

Arquivos:

- `src/personality.py`;
- `src/context_engine.py`;
- `src/casual_handlers.py`;
- `src/personality_navigation.py`;
- `src/scheduler.py`.

Personalidade: competente, informal, levemente cansado/cínico e útil. Pode provocar a situação/comportamento, nunca humilhar o usuário.

Tons:

- `NEUTRO`;
- `LEVE`;
- `SARCASTICO`;
- `CUIDADOSO`.

Day-off e situações sensíveis permanecem sem sarcasmo.

A personalidade aparece em menus frequentes, cumprimentos, agradecimentos e lembretes. O contexto atual já observa pendências/atrasos e há um traço recorrente de antipatia por terça-feira.

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
- tradução de códigos SIGAA;
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

Trata aulas, tarefas/compromissos/pendências, itens adiados, rotinas e Day-off. Lembretes passam pelo Personality Engine e já usam `preferred_name` quando cadastrado.

## Finanças

Continua planejado, ainda sem persistência real. Direção: entradas/saídas, categorias, saldo mensal, histórico, detecção de excesso, economia e metas.

## Próximos passos sugeridos

1. validar importação de grade com screenshot/PDF real no Telegram;
2. validar o onboarding/nome preferido nas duas versões;
3. validar que `main_generic` nasce realmente sem grade e sem Protocol Mass;
4. depois retomar resumo diário + personalidade contextual baseada em comportamento;
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
