# Etapa 4.5 — Importação de Cursos e Materiais

**Status:** implementada na branch da Etapa 4.

## Objetivo

Importar uma estrutura de curso sem transformar texto ambíguo em dados inventados. O fluxo é determinístico, aceita `.txt`, PDF textual ou texto colado e sempre exige prévia + confirmação.

## Formato suportado

```text
CURSO: Java + Spring
TIPO: AUTOGERIDO
DESCRICAO: Trilha backend
[MÓDULO] Fundamentos
[CONTEÚDO] REST Controllers | aula
[MATERIAL] Slides | link | https://exemplo.com
[ATIVIDADE] Exercícios | implementar GET /health
```

Para curso ao vivo:

```text
TIPO: AO VIVO
[CONTEÚDO] Aula síncrona | aula | 15/09/2026 19:30
```

Tipos de conteúdo aceitos: aula, leitura, exercício, projeto, revisão e outro. Materiais aceitam link, arquivo, vídeo, texto e outro.

## Segurança da importação

- PDF precisa possuir texto pesquisável; não há OCR;
- arquivo é limitado antes de parsing;
- linhas desconhecidas bloqueiam a importação em vez de serem adivinhadas;
- material/atividade sem conteúdo-pai bloqueia a importação;
- datas fixas no formato de importação só entram em curso `AO VIVO`;
- limites de módulos, conteúdos e filhos evitam payload descontrolado;
- o plano inteiro é validado antes da primeira escrita;
- a prévia não grava nada;
- persistência só ocorre após `✅ Confirmar importação`;
- todas as escritas são orquestradas pelas funções de `course_domain.py`;
- conteúdos e atividades importados começam pendentes.

## Implementação

- `cloudflare/src/course_importer.py` — leitura, parser, validação, prévia e orquestração;
- `cloudflare/src/course_stage4.py` — wizard Telegram `📥 Importar curso`;
- `cloudflare/tests/test_stage4_5_course_import.py` — parser, ambiguidades, calendário, prévia obrigatória e persistência.

O menu estruturado `📘 Cursos` continua separado do backlog `🎓 Cursos` de Ler/Ver Depois.
