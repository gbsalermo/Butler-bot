# Continuidade do desenvolvimento

## Estado atual

- Repositório inicializado.
- Branch de desenvolvimento: `feat/base-inicial`.
- Stack inicial: Python, python-telegram-bot, SQLite e python-dotenv.
- Objetivo da etapa: executar o Butler localmente via polling, registrar o chat_id do usuário e manter a grade acadêmica persistida.

## Grade base do semestre

- Álgebra Linear I: terça e quinta, 10:00–11:40, PAV III Sala 10.
- Física II: segunda e quarta, 10:00–11:40, PAV III Sala 07.
- Laboratório de Sistemas Digitais I: segunda, 14:00–16:00, PAV Eng. Sala D6. Horário corrigido manualmente.
- Princípios de Eletrônica Analógica: terça e quinta, 08:01–09:40, PAV I Sala 104.
- Sistemas Digitais I: segunda 08:01–09:40 PAV I Sala 11; quarta 08:01–09:40 PAV I Sala 114.

## Próximos passos

1. Finalizar a camada SQLite e seed da grade.
2. Implementar `/start` e persistência do `chat_id`.
3. Implementar `/materias`.
4. Implementar botão `➕ Adicionar matéria` com cadastro guiado.
5. Adicionar scheduler e avisos automáticos antes das aulas.
6. Evoluir para tarefas, compromissos, ônibus e autocuidado.

## Regra do projeto

Ao concluir uma etapa relevante, atualizar este arquivo e o README para manter o contexto entre sessões de desenvolvimento.
