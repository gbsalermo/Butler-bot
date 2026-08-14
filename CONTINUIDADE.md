# Continuidade do desenvolvimento

## Estado atual

- Desenvolvimento inicial concentrado na branch `main` por decisão do projeto.
- Stack atual: Python, `python-telegram-bot`, SQLite e `python-dotenv`.
- Execução local via polling.
- `/start` registra e atualiza o `chat_id` do usuário no SQLite.
- A grade acadêmica do semestre é carregada automaticamente no primeiro uso.
- `/materias` e o botão `📚 Minhas matérias` listam as disciplinas cadastradas.
- O botão `➕ Adicionar matéria` inicia um cadastro guiado pelo Telegram.

## Grade base do semestre

- Álgebra Linear I: terça e quinta, 10:00–11:40, PAV III Sala 10.
- Física II: segunda e quarta, 10:00–11:40, PAV III Sala 07.
- Laboratório de Sistemas Digitais I: segunda, 14:00–16:00, PAV Eng. Sala D6. Horário corrigido manualmente.
- Princípios de Eletrônica Analógica: terça e quinta, 08:01–09:40, PAV I Sala 104.
- Sistemas Digitais I: segunda 08:01–09:40 PAV I Sala 11; quarta 08:01–09:40 PAV I Sala 114.

## Banco atual

Tabelas:

- `users`: armazena `telegram_chat_id`, dados básicos do usuário e datas de atualização.
- `subjects`: cadastro das disciplinas.
- `class_sessions`: dias, horários e locais associados a cada disciplina.

O banco local é criado em `data/butler.db` por padrão e não é versionado.

## Fluxos implementados

### Inicialização

1. Executar `python -m src.main`.
2. O banco é criado se necessário.
3. Se ainda não houver matérias, a grade base é cadastrada automaticamente.
4. O bot entra em polling.
5. `/start` registra o chat atual e apresenta o menu principal.

### Adicionar matéria

1. Pressionar `➕ Adicionar matéria` ou usar `/adicionar_materia`.
2. Informar nome.
3. Informar dias separados por vírgula, por exemplo `seg, qua`.
4. Informar horário inicial no formato `HH:MM`.
5. Informar horário final no formato `HH:MM`.
6. Informar sala/local.
7. A matéria e suas aulas são persistidas no SQLite.

Use `/cancelar` durante o cadastro para interromper o fluxo.

## Próxima etapa prioritária

Implementar o núcleo proativo do Butler:

1. Scheduler executando junto ao bot.
2. Consulta das próximas aulas do dia.
3. Aviso automático aproximadamente 10 minutos antes da aula.
4. Estrutura reutilizável para compromissos, tarefas e rotinas.
5. Botões de confirmação/adiamento para lembretes.

Depois disso, adicionar tarefas, compromissos, ônibus e autocuidado.

## Decisões importantes

- A primeira fase permanece simples e local antes da hospedagem 24/7.
- O `chat_id` deve ficar persistido porque o Butler precisará iniciar mensagens proativamente.
- Aula é tratada separadamente de tarefa e compromisso, pois possui disciplina, recorrência semanal, horário e sala.
- O horário de Laboratório de Sistemas Digitais I não segue o código exibido pelo SIGAA; usar 14:00–16:00 na segunda-feira até nova atualização.

## Regra de continuidade

Ao concluir uma etapa relevante:

1. atualizar este arquivo com o estado real;
2. atualizar o `README.md` quando houver mudança de instalação, comandos ou funcionalidades;
3. registrar decisões que afetem etapas futuras;
4. deixar explícito o próximo passo técnico.
