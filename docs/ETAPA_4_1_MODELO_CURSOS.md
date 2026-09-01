# Etapa 4.1 — Modelo e autoridade de Cursos

**Status:** 🚧 implementação inicial  
**Etapa:** 4 — Cursos e trilhas de estudo

## Objetivo

Criar a base persistente e uma única autoridade de domínio para cursos antes de adicionar menus, linguagem natural ou importadores.

O modelo nasce preparado para dois tipos de curso:

```text
self_paced
→ usuário avança explicitamente no próprio ritmo

live
→ conteúdos podem ter calendário/horário fixo
```

## Modelo

```text
courses
└── course_modules[]
    └── course_contents[]
        ├── course_materials[]
        └── course_activities[]

course_events
→ histórico explícito de mudanças relevantes
```

Migration formal:

```text
cloudflare/migrations/0013_courses.sql
```

Autoridade de domínio:

```text
cloudflare/src/course_domain.py
```

## Invariantes

1. Curso é sempre isolado por `user_id`.
2. Módulos e conteúdos possuem ordem explícita por `position`.
3. Consultar o próximo conteúdo nunca altera progresso.
4. Tempo decorrido nunca conclui conteúdo.
5. Modo Estudo nunca deve concluir conteúdo por conta própria.
6. Conteúdo muda para `completed` ou `skipped` somente por ação explícita.
7. Atividade possui progresso próprio e não conclui o conteúdo-pai automaticamente.
8. Curso também só recebe status `completed` explicitamente.
9. `skipped` conta como resolvido, mas não como concluído.
10. Cursos ao vivo podem usar `scheduled_at`; conteúdos sem data continuam válidos como materiais/trilha complementar.
11. Migration é a fonte formal do schema.
12. `course_domain.py` não interpreta linguagem e não envia mensagens Telegram.

## Estados

### Curso

```text
active
paused
completed
archived
```

### Conteúdo/atividade

```text
pending
completed
skipped
```

## Tipos de conteúdo

```text
lesson
reading
exercise
project
review
other
```

## Tipos de material

```text
link
file
video
text
other
```

## Operações da autoridade

```text
create_course
add_module
add_content
add_material
add_activity
set_content_status
set_activity_status
set_course_status
next_content
progress_summary
course_structure
```

A camada de Telegram da Etapa 4.2 deve chamar essas operações em vez de escrever SQL próprio de cursos.

## Progresso

O resumo separa:

```text
total
completed
skipped
pending
percent_completed
percent_resolved
```

Isso evita apresentar conteúdo pulado como se tivesse sido estudado.

## Curso autogerido

`next_content()` usa:

```text
posição do módulo
→ posição do conteúdo
```

## Curso ao vivo

`next_content()` usa primeiro conteúdos com `scheduled_at`, em ordem cronológica, e depois conteúdos sem agenda.

Essa regra ainda não significa "aula ocorreu" ou "aula foi assistida". É apenas ordenação.

## Testes da 4.1

A regressão específica cobre:

- estrutura ordenada;
- ausência de progresso automático;
- conclusão explícita do conteúdo;
- conclusão explícita do curso;
- `skipped` separado de `completed`;
- curso ao vivo por agenda;
- materiais e atividades;
- atividade não concluindo conteúdo-pai;
- isolamento entre usuários;
- constraints de enums no D1.

Arquivo:

```text
cloudflare/tests/test_stage4_1_course_domain.py
```

## Fora da 4.1

Ainda não entra nesta subetapa:

- menu `📚 Cursos` operacional;
- wizard de criação/edição;
- linguagem natural de cursos;
- importação de estrutura de cursos;
- upload/associação real de arquivos;
- integração com Modo Estudo;
- migração automática dos itens `🎓 Cursos` de Ler/Ver Depois.

Esses pontos entram gradualmente nas próximas subetapas.

## Próximo passo — 4.2

Criar CRUD/navegação operacional sobre `course_domain.py`:

```text
Cursos
├── Meus cursos
├── Adicionar curso
├── Abrir curso
│   ├── módulos
│   ├── conteúdos
│   └── progresso
└── Editar/arquivar
```

Depois disso entra o fluxo de **Continuar curso**, integração com Modo Estudo e importação.
