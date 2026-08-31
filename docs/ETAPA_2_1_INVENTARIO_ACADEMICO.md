# Butler — Etapa 2: Importação acadêmica confiável

**Data-base:** 31/08/2026  
**Status:** escopo corrigido após validação do produto  
**Etapa anterior:** Etapa 1 concluída

## Decisão de produto

O modelo acadêmico atual do Butler já atende bem ao uso esperado e **não deve ser reformulado nesta etapa**.

A Etapa 2 tem um objetivo específico:

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

`app.parse_schedule_text()` já extrai `name`, `weekday`, `start`, `end`, `location` e `code`.

Exemplo:

```text
Sistemas Digitais I 35M45 PAV II sala 05
```

vira duas sessões, terça e quinta, de 10:00–12:00 no mesmo local.

O `code` pode continuar apenas como dado intermediário do parser; não precisa virar novo campo no banco nesta etapa.

O fluxo atual de preview também deve ser preservado:

```text
arquivo
→ extração
→ prévia
→ usuário confere
→ confirmação
→ cadastro
```

Cadastro manual continua sendo alternativa válida quando o arquivo não puder ser interpretado com confiança.

---

## 4. Problema real que a Etapa 2 deve resolver

O objetivo é diminuir casos como:

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

O Butler deve preferir dizer que não conseguiu interpretar uma linha a inventar ou cadastrar grade errada.

---

## 5. Ordem da Etapa 2

### 2.1 — Caracterizar o comportamento atual ✅

- parser SIGAA identificado;
- fonte recomendada confirmada;
- PDF textual/TXT confirmados;
- sem OCR confirmado;
- múltiplos dias e blocos M/T/N caracterizados;
- localização opcional caracterizada;
- falsos positivos básicos cobertos;
- edição atual reconhecida como suficiente;
- testes de caracterização adicionados.

### 2.2 — Extração SIGAA mais robusta

Melhorar leitura de nome, local, espaços/quebras de linha, códigos com múltiplos dias, combinações M/T/N, cabeçalhos/rodapés e texto repetido pelo PDF.

Sem alterar o modelo persistido.

### 2.3 — Validação e confiança

Classificar cada bloco como:

```text
✅ reconhecido
⚠️ precisa conferir
❌ não reconhecido
```

Bloquear nome vazio, horário impossível, código parcialmente reconhecido, duplicata e linha ambígua.

### 2.4 — Prévia mais clara

Mostrar exatamente matérias, dias, horários e locais que serão cadastrados, além de qualquer linha ambígua/rejeitada.

### 2.5 — Cadastro inicial seguro

Após confirmação:

- cadastrar somente o que apareceu na prévia;
- manter `subjects` + `subject_sessions` como hoje;
- evitar duplicatas na própria importação;
- manter isolamento por usuário;
- não cadastrar trecho ambíguo/rejeitado;
- limpar corretamente o estado do wizard.

O foco oficial é **novo usuário / primeira grade**.

Reimportação de grade existente não é objetivo desta etapa.

### 2.6 — Onboarding e regressão real

Explicar onde pegar a grade no SIGAA, tabela recomendada, PDF textual/TXT, ausência de OCR, prévia antes de salvar e alternativa de cadastro manual.

Adicionar corpus com exemplos reais/anônimos.

---

## 6. Gate de saída

- [ ] principais variações reais do SIGAA reconhecidas com segurança;
- [ ] múltiplos dias/horários extraídos corretamente;
- [ ] cabeçalhos/rodapés/linhas irrelevantes ignorados;
- [ ] duplicatas da própria importação eliminadas;
- [ ] blocos ambíguos sinalizados;
- [ ] prévia clara;
- [ ] nada persistido antes da confirmação;
- [ ] cadastro final usa o modelo acadêmico atual;
- [ ] onboarding de novos usuários validado;
- [ ] cadastro manual preservado;
- [ ] isolamento multiusuário;
- [ ] regressão completa verde.

**Não é requisito da Etapa 2 modificar o schema acadêmico atual.**

---

## 7. Observações técnicas fora do escopo

O inventário encontrou pontos sobre reimportação de usuários existentes e associações históricas. Eles podem ser revisitados se surgirem como problema real, mas **não devem puxar a Etapa 2 para uma reformulação acadêmica** sem nova decisão explícita.

---

## Próximo passo

Fechar a PR 2.1 e iniciar **2.2 — Extração SIGAA mais robusta**, sem migration e sem alterar o formato atual das matérias.
