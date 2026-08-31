# Butler — Etapa 2: Importação acadêmica confiável

**Data-base:** 31/08/2026  
**Status:** escopo corrigido após validação do produto  
**Etapa anterior:** Etapa 1 concluída

## Decisão de produto

O modelo acadêmico atual do Butler já atende bem ao uso esperado e **não deve ser reformulado nesta etapa**.

A Etapa 2 passa a ter um objetivo específico:

> aumentar a confiança na extração e no cadastro inicial das matérias de novos usuários.

Portanto, ficam fora do escopo desta etapa, salvo correção mínima de bug explicitamente aprovada:

- redesenhar `subjects` / `subject_sessions`;
- adicionar professor, carga horária, observações ou semestre;
- criar modelo novo de avaliações/trabalhos;
- refatorar presença/faltas;
- alterar a experiência atual de edição manual de matérias;
- criar migrations apenas por melhoria arquitetural;
- substituir o formato acadêmico que já funciona.

O formato atual deve ser **preservado**.

---

## 1. O que já funciona e deve continuar igual

O Butler já representa matéria e aulas de forma suficiente para o produto atual:

```text
subjects
→ nome
→ ativa/trancada

subject_sessions
→ dia da semana
→ horário inicial
→ horário final
→ local
```

Uma matéria pode ter múltiplos horários/localizações.

Também já existem:

- cadastro manual;
- edição de nome/dia/horário/local;
- adicionar/remover aula;
- trancar/remover matéria;
- provas;
- faltas e limite de faltas;
- avisos de aula;
- consultas naturais;
- importação por PDF textual/TXT.

Nada disso precisa ser remodelado nesta etapa.

---

## 2. Fonte recomendada para novos usuários

A fonte oficial recomendada permanece a tabela do painel principal do SIGAA:

```text
Componente Curricular | Local | Horário
```

Exemplos de códigos aceitos pelo parser atual:

```text
35M45
24M23
2T23
```

Formatos aceitos:

- PDF com texto pesquisável/selecionável;
- TXT.

Não usar OCR em produção para print, foto, imagem ou PDF escaneado.

O onboarding atual que orienta `Imprimir → Salvar como PDF` diretamente do SIGAA deve ser mantido.

---

## 3. O que o inventário confirmou

### Parser atual

`app.parse_schedule_text()` já extrai:

```text
name
weekday
start
end
location
code
```

Exemplo:

```text
Sistemas Digitais I 35M45 PAV II sala 05
```

vira duas sessões:

```text
terça-feira   10:00–12:00  PAV II sala 05
quinta-feira 10:00–12:00  PAV II sala 05
```

O `code` faz parte da saída do parser, mas não precisa virar novo campo no banco nesta etapa.

### Preview

A decisão atual é boa e permanece obrigatória:

```text
arquivo
→ extração
→ prévia
→ usuário confere
→ confirmação
→ cadastro
```

Não haverá `parser → banco` silencioso.

### Cadastro manual

Continua sendo alternativa válida quando o arquivo não puder ser interpretado com confiança.

---

## 4. Problema real que a Etapa 2 deve resolver

O objetivo não é adicionar mais informação às matérias. É diminuir casos como:

```text
matéria não reconhecida
nome cortado
local grudado no nome
código SIGAA interpretado errado
um código com dois dias virar só uma aula
horário M/T/N convertido incorretamente
linha irrelevante virar matéria
matéria duplicada na mesma importação
arquivo parcialmente entendido ser cadastrado como se estivesse correto
```

O Butler deve preferir:

> "Não consegui interpretar estas 2 linhas; confira antes de cadastrar."

em vez de inventar ou cadastrar grade errada.

---

## 5. Ordem da Etapa 2

### 2.1 — Caracterizar o comportamento atual ✅

- [x] parser SIGAA identificado;
- [x] fonte recomendada confirmada;
- [x] PDF textual/TXT confirmados;
- [x] sem OCR confirmado;
- [x] múltiplos dias do mesmo código caracterizados;
- [x] blocos M/T/N caracterizados;
- [x] localização opcional caracterizada;
- [x] falsos positivos básicos cobertos;
- [x] edição atual reconhecida como suficiente;
- [x] testes de caracterização adicionados.

### 2.2 — Extração SIGAA mais robusta

Melhorar a leitura sem alterar o modelo persistido.

Cobrir variações reais de:

```text
nome da matéria
código da turma/componente quando aparecer na linha
local vazio ou longo
espaços/quebras de linha do PDF
códigos com mais de um dia
combinações M/T/N
linhas de cabeçalho/rodapé
texto repetido pelo PDF
```

O parser deve continuar determinístico.

### 2.3 — Validação e confiança

Antes da prévia, validar cada matéria/sessão.

Exemplos de erro que devem bloquear o cadastro daquele bloco:

- nome vazio;
- dia inválido;
- horário impossível;
- código SIGAA parcialmente reconhecido;
- sessão duplicada dentro do mesmo arquivo;
- linha ambígua que poderia representar mais de uma matéria.

Classificação desejada:

```text
✅ reconhecido
⚠️ precisa conferir
❌ não reconhecido
```

### 2.4 — Prévia mais clara

O usuário deve conseguir conferir facilmente o resultado antes de salvar.

Exemplo:

```text
📥 Encontrei 6 matérias

1. Cálculo II
   terça 08:00–10:00 — PAV I 03
   quinta 08:00–10:00 — PAV I 03

2. Física II
   quarta 14:00–16:00 — Lab. Física

⚠️ Não consegui interpretar:
• linha: "..."

[✅ Confirmar cadastro]
[❌ Cancelar]
```

Se houver bloco ambíguo, o Butler não deve fingir confiança total.

### 2.5 — Cadastro inicial seguro

Ao confirmar:

- cadastrar somente o que apareceu na prévia;
- preservar o formato atual de `subjects` + `subject_sessions`;
- evitar duplicatas dentro da mesma importação;
- isolar tudo por usuário;
- não cadastrar trecho rejeitado/ambíguo;
- limpar corretamente o estado do wizard após confirmar/cancelar.

O foco oficial é **novo usuário / primeira grade**.

Reimportação de uma grade já existente não é objetivo desta etapa. Os riscos técnicos encontrados no inventário ficam documentados, mas não justificam redesenhar o sistema agora.

### 2.6 — Onboarding e regressão real

Primeiro acesso deve explicar:

1. onde pegar a grade no SIGAA;
2. qual tabela usar;
3. PDF textual ou TXT;
4. por que print/scan não funciona;
5. que haverá uma prévia antes do cadastro;
6. que cadastro manual continua disponível.

Criar corpus com exemplos reais/anônimos de grades e variações de PDF/TXT.

---

## 6. Gate de saída da Etapa 2

A Etapa 2 estará concluída quando:

- [ ] parser reconhecer com segurança as principais variações reais do SIGAA;
- [ ] múltiplos dias/horários forem extraídos corretamente;
- [ ] cabeçalhos/rodapés/linhas irrelevantes não virarem matéria;
- [ ] duplicatas da própria importação forem eliminadas;
- [ ] blocos ambíguos forem sinalizados em vez de inventados;
- [ ] prévia mostrar claramente tudo que será cadastrado;
- [ ] nada for persistido antes da confirmação;
- [ ] cadastro final usar o mesmo modelo acadêmico atual;
- [ ] onboarding de novos usuários explicar o formato recomendado;
- [ ] cadastro manual continuar disponível;
- [ ] dois usuários permanecerem isolados;
- [ ] regressão completa ficar verde.

**Não é requisito da Etapa 2 modificar o schema acadêmico atual.**

---

## 7. Observações técnicas fora do escopo

O inventário encontrou pontos que podem ser revisitados apenas se um caso real exigir no futuro, como comportamento de reimportação de usuário já existente e associações históricas.

Eles **não devem puxar a Etapa 2 para uma reformulação acadêmica** sem nova decisão explícita do produto.

---

## Próximo passo

Fechar a PR 2.1 mantendo os testes de caracterização e iniciar **2.2 — Extração SIGAA mais robusta**, sem migration e sem alterar o formato atual das matérias.
