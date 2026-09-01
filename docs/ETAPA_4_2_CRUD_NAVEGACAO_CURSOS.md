# Etapa 4.2 — CRUD e navegação de Cursos

**Status:** ✅ concluída  
**Data:** 01/09/2026  
**Implementação principal:** PR #43  
**Merge funcional:** `4987327cae69e16d9973bee4a97aa3229c36f5d2`

---

## Objetivo

Transformar o modelo autoritativo criado na Etapa 4.1 em uma experiência operacional no Telegram, sem antecipar progresso, Modo Estudo ou importação.

A 4.2 entrega navegação e manutenção estrutural. Ela **não** autoriza concluir conteúdos por tempo, por abertura de tela ou por edição.

---

## Entrada no Telegram

O menu principal ganhou uma área própria:

```text
📘 Cursos
```

Ela é deliberadamente diferente de:

```text
🎓 Cursos
```

que continua sendo apenas a categoria simples de `Ler/Ver Depois`.

O layout protegido do menu foi preservado:

- `📖 Manual` continua em linha própria;
- `🌙 Day-off` continua sozinho na última linha para reduzir toque acidental.

---

## Fluxos entregues

### Cursos

```text
📘 Cursos
├── 📚 Meus cursos
├── ➕ Novo curso
├── 🗄️ Cursos arquivados
└── abrir curso por botão/ID
```

Ao criar um curso, o Butler pergunta:

1. nome;
2. tipo:
   - `🧭 Autogerido` → `self_paced`;
   - `📡 Ao vivo` → `live`;
3. descrição opcional.

### Tela do curso

Mostra:

- nome;
- tipo;
- status;
- descrição;
- quantidade de módulos;
- conteúdos totais;
- concluídos;
- pulados;
- pendentes;
- percentual concluído;
- percentual resolvido quando houver pulos.

Nesta etapa o progresso é **somente leitura**.

### Edição do curso

É possível alterar:

- nome;
- descrição;
- tipo `self_paced/live`.

Alterar metadados nunca altera progresso.

### Arquivamento

A remoção operacional adotada na Etapa 4.2 é **arquivar**, não hard delete.

```text
curso ativo
→ confirmação explícita
→ archived
```

Estrutura, conteúdos, materiais, atividades e histórico são preservados.

Cursos arquivados podem ser reativados:

```text
archived → active
```

---

## Módulos

Dentro do curso:

```text
🧩 Módulos
├── abrir módulo
├── ➕ Novo módulo
└── ✏️ Renomear módulo
```

A posição continua sendo determinada pelo domínio autoritativo e respeita a ordem persistida.

---

## Conteúdos

Dentro de cada módulo:

```text
📄 Conteúdo
├── abrir
├── ➕ Novo conteúdo
└── ✏️ Editar conteúdo
```

Tipos disponíveis:

```text
lesson   → 🎥 Aula
reading  → 📖 Leitura
exercise → 🧪 Exercício
project  → 🛠️ Projeto
review   → 🔁 Revisão
other    → 📎 Outro
```

É possível editar:

- nome;
- tipo;
- data/horário.

Cursos ao vivo pedem data/horário ao criar conteúdo, com formato de entrada:

```text
DD/MM/AAAA HH:MM
```

Persistência normalizada:

```text
YYYY-MM-DDTHH:MM
```

Também é permitido deixar o conteúdo sem data fixa.

---

## Autoridade de domínio

`cloudflare/src/course_domain.py` continua sendo a única autoridade de persistência de Cursos.

A 4.2 adicionou operações de aplicação necessárias ao Telegram:

```text
list_courses()
get_course()
update_course()
rename_module()
update_content()
content_details()
```

A camada `course_operational.py` mantém apenas conversa/wizard e chama a autoridade para qualquer escrita.

Não existe SQL de mutação de curso espalhado pelo handler do Telegram.

---

## Invariantes preservados

### Progresso explícito

Continuam verdadeiras:

```text
abrir conteúdo      ≠ concluir
editar conteúdo     ≠ concluir
passar o tempo      ≠ concluir
criar módulo        ≠ avançar curso
navegar             ≠ progresso
```

A Etapa 4.3 será responsável por expor ao usuário as mudanças explícitas de progresso.

### Multiusuário

Um usuário não pode listar, abrir ou editar curso, módulo ou conteúdo de outro usuário.

### Curso ao vivo

Editar tipo/data não desloca automaticamente aulas futuras nem inventa presença/conclusão.

### Cancelamento

Wizard cancelado não deixa curso parcial persistido quando a criação ainda não foi confirmada.

---

## Regressão

Gate final da PR funcional:

```text
366 passed
```

A regressão encontrou e corrigiu antes do merge:

1. conflito de layout com a linha protegida do `📖 Manual`;
2. recuperação tardia do estado do wizard em chamadas isoladas;
3. `variation selector` invisível do emoji `🗄️`, que impedia reabrir curso arquivado para reativação.

Nenhum desses problemas foi mascarado alterando os testes antigos.

---

## Fora de escopo desta etapa

Ainda não pertence à 4.2:

- concluir conteúdo;
- pular conteúdo;
- voltar conteúdo para pendente;
- `Continuar curso`;
- sugestão do próximo conteúdo;
- concluir curso pelo Telegram;
- integração com Modo Estudo;
- importar estrutura de curso;
- reformulação final do menu por áreas da vida.

---

## Próxima subetapa

**4.3 — Progresso e `Continuar curso`.**

Deve usar as operações explícitas já existentes no domínio (`set_content_status`, `next_content`, `progress_summary`) para expor uma UX segura, mantendo a regra:

> o Butler só registra avanço quando o usuário explicitamente conclui ou pula o conteúdo.

Somente depois da 4.3 deve começar a integração operacional com Modo Estudo da 4.4.
