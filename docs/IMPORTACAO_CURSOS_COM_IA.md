# Importação de cursos com apoio de IA

O botão `📥 Importar curso` mostra ao usuário o formato aceito pelo Butler e um prompt pronto para converter currículos que estejam em imagem, print, PDF escaneado ou texto bruto.

A IA é apenas uma etapa de preparação do texto. O importador do Butler continua determinístico: ele aceita somente o formato explícito, valida tudo, mostra uma prévia e só persiste depois de `✅ Confirmar importação`.

## Formato-base

```text
CURSO: Nome do curso
TIPO: AUTOGERIDO
DESCRICAO: descrição curta
[MÓDULO] Nome do módulo
[CONTEÚDO] Nome do conteúdo | aula
[MATERIAL] Nome do material | arquivo | referência
[ATIVIDADE] Nome da atividade | observação
```

Cursos ao vivo podem usar uma terceira coluna em `[CONTEÚDO]` somente quando a data/horário estiver realmente explícita:

```text
TIPO: AO VIVO
[CONTEÚDO] Aula síncrona | aula | 15/09/2026 19:30
```

Linhas iniciadas por `#` podem ser usadas pela IA para registrar pendências/trechos ilegíveis sem quebrar o parser.

O prompt exibido no Telegram exige que a IA preserve a ordem real, não invente dados e devolva somente o texto no formato Butler.
