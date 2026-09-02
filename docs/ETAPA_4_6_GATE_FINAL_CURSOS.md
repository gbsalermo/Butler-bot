# Etapa 4.6 — Gate final de Cursos e Trilhas

**Status:** ✅ aprovado  
**PR final:** #46 — `feat: concluir Etapa 4 de Cursos até o gate final`.

> O PR draft #45 foi fechado sem merge por uma limitação do conector ao convertê-lo para Ready. O PR #46 substitui aquele com a mesma branch/conteúdo funcional e é o PR de merge desta etapa.

## Escopo validado

O gate cobre o domínio estruturado `📘 Cursos` das subetapas 4.1 a 4.5:

- modelo/autoridade em `course_domain.py`;
- CRUD e navegação Telegram;
- progresso explícito e `▶️ Continuar curso`;
- conclusão/pulo/reabertura de conteúdo;
- conclusão/reabertura explícita do curso;
- ordenação autogerida por posição;
- ordenação de curso ao vivo pelo calendário persistido;
- integração com Modo Estudo sem conclusão implícita;
- importação TXT/PDF textual com parser determinístico, prévia e confirmação;
- materiais/atividades agrupados no conteúdo correto;
- isolamento multiusuário;
- histórico por `course_events`.

## Invariantes de aceite

```text
abrir/navegar                   ≠ concluir conteúdo
Continuar curso                 ≠ concluir conteúdo
tempo de foco                   ≠ concluir conteúdo
fim de tópico/sessão de estudo ≠ concluir conteúdo
último conteúdo resolvido       ≠ concluir curso
prévia de importação            ≠ persistir curso
```

Mudanças reais continuam exigindo ação explícita.

## Migrations formais

```text
0013_courses.sql
0014_course_study_links.sql
```

`ensure_schema()` permanece apenas como tolerância operacional onde aplicável; migrations são a fonte formal.

## Regressão adicionada

```text
test_stage4_3_course_progress.py
test_stage4_4_course_study_bridge.py
test_stage4_5_course_import.py
test_stage4_6_course_gate.py
```

O gate integrado verifica, entre outros casos:

1. sequência de `next_content()` em curso autogerido;
2. calendário persistido em curso ao vivo;
3. histórico de conclusão/pulo/conclusão de curso;
4. importação → Modo Estudo → conclusão explícita como domínios separados;
5. bloqueio de acesso cruzado entre usuários;
6. prévia de importação sem efeitos colaterais.

## Evidência de CI

O commit de gate integrado `7b41c42d4f151b126f405c7be9bceffcd452b9f9` passou no GitHub Actions `Butler regression` run #286, incluindo `Compile Worker sources` e `Run deterministic regression suite`.

A documentação final da branch também foi submetida ao mesmo workflow. O **head final do PR #46 deve estar verde antes do merge**, e o workflow de `main` deve ser conferido depois do merge.

## O que NÃO entra neste gate

A reorganização do menu por áreas da vida não foi antecipada. Ela é o **fechamento obrigatório da Etapa 4**, executado depois deste gate e antes da Etapa 5.

Também não entra IA/Groq; essa trilha continua pós-Etapa 11 + gate de estabilidade.

## Próximo ponto oficial após este gate

**Fechamento da Etapa 4 — reorganizar o menu por áreas da vida.**

Somente depois desse fechamento o roadmap pode avançar para a **Etapa 5 — Caixa de entrada**.
