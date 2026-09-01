# Etapa 4.4 — Integração de Cursos com Modo Estudo

**Status:** implementada na branch da Etapa 4.

## Objetivo

Permitir iniciar o Modo Estudo diretamente de um conteúdo pendente sem misturar as autoridades dos dois domínios e sem transformar tempo estudado em progresso fictício.

## Fluxo

Na tela de um conteúdo pendente de curso ativo aparece:

`🧠 Estudar no Modo Estudo`

A ação:

1. valida que curso/conteúdo pertencem ao usuário;
2. exige curso `active` e conteúdo `pending`;
3. recusa substituir silenciosamente uma sessão de estudo já ativa/pausada;
4. cria sessão com o título do curso como assunto e o conteúdo como tópico;
5. persiste o vínculo em `course_study_links`;
6. mantém o conteúdo do curso `pending`.

Ao concluir/pular o tópico ou terminar a sessão no Modo Estudo, o conteúdo do curso continua inalterado. O usuário volta à tela do conteúdo e usa a ação explícita de concluir/pular quando isso representar o que realmente ocorreu.

## Persistência

Migration formal:

`cloudflare/migrations/0014_course_study_links.sql`

A tabela liga:

- `user_id`;
- `course_id`;
- `content_id`;
- `study_session_id`.

A exclusão em cascata acompanha os domínios existentes, mas o histórico normal nunca depende de hard delete operacional.

## Implementação

- `cloudflare/src/course_study_bridge.py` — ponte entre os domínios;
- `cloudflare/src/course_stage4.py` — botão/UX;
- `cloudflare/tests/test_stage4_4_course_study_bridge.py` — regressões de independência, conflito de sessão e isolamento.

## Invariantes

- tempo não conclui conteúdo;
- fim de foco não conclui conteúdo;
- fim da sessão não conclui conteúdo;
- o Modo Estudo continua governando apenas sua própria sessão/tópicos;
- `course_domain.py` continua sendo a autoridade de progresso de Cursos.
