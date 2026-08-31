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

## O que já funciona e deve continuar igual

O Butler já representa matéria e aulas de forma suficiente:

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

Uma matéria pode ter múltiplos horários/localizações. Cadastro manual, edição, provas, faltas, avisos acadêmicos e consultas naturais permanecem como estão.

---

## Fonte recomendada para novos usuários

A fonte oficial permanece a tabela do painel principal do SIGAA:

```text
Componente Curricular | Local | Horário
```

Formatos aceitos:

- PDF com texto pesquisável/selecionável;
- TXT.

Print, foto, imagem ou PDF escaneado continuam fora do fluxo porque o Butler não usa OCR em produção.

---

## Objetivo técnico real

Melhorar a confiabilidade do parser atual para evitar:

```text
matéria não reconhecida
nome cortado
local grudado no nome
código SIGAA interpretado errado
um código com dois dias virar só uma aula
horário M/T/N convertido incorretamente
linha irrelevante virar matéria
matéria duplicada na mesma importação
arquivo parcialmente entendido ser cadastrado como correto
```

Em caso de dúvida, o Butler deve sinalizar a linha para conferência em vez de inventar.

---

## Ordem da Etapa 2

### 2.1 — Caracterização do comportamento atual ✅

Parser, múltiplos dias, blocos M/T/N, localização opcional, falsos positivos básicos e onboarding já possuem testes de caracterização.

### 2.2 — Extração SIGAA mais robusta

Tratar melhor espaços/quebras de linha, locais, códigos com múltiplos dias, combinações M/T/N, cabeçalhos/rodapés e texto repetido pelo PDF, sem alterar o modelo persistido.

### 2.3 — Validação e confiança

Classificar blocos:

```text
✅ reconhecido
⚠️ precisa conferir
❌ não reconhecido
```

Evitar nome vazio, horário impossível, código parcialmente reconhecido, duplicata e linha ambígua.

### 2.4 — Prévia clara

Mostrar exatamente matéria, dias, horários e local de tudo que será salvo, além de qualquer trecho ambíguo/rejeitado.

### 2.5 — Cadastro inicial seguro

Após confirmação:

- salvar somente o que apareceu na prévia;
- manter `subjects` + `subject_sessions` como hoje;
- evitar duplicatas dentro da importação;
- manter isolamento por usuário;
- não salvar bloco ambíguo/rejeitado;
- limpar o wizard corretamente.

Foco oficial: **novo usuário / primeira grade**.

Reimportação de grade existente não é objetivo desta etapa.

### 2.6 — Onboarding + regressão real

Explicar onde obter a grade, formato recomendado, PDF/TXT, ausência de OCR, prévia e cadastro manual. Adicionar exemplos reais/anônimos ao corpus.

---

## Gate de saída

- [ ] principais variações reais do SIGAA reconhecidas com segurança;
- [ ] múltiplos dias/horários corretos;
- [ ] cabeçalhos/rodapés/linhas irrelevantes ignorados;
- [ ] duplicatas internas eliminadas;
- [ ] ambiguidades sinalizadas;
- [ ] prévia clara;
- [ ] nada salvo antes de confirmação;
- [ ] mesmo modelo acadêmico atual no cadastro final;
- [ ] onboarding de novos usuários validado;
- [ ] cadastro manual preservado;
- [ ] isolamento multiusuário;
- [ ] regressão completa verde.

**Não é requisito da Etapa 2 modificar o schema acadêmico atual.**

---

## Observações fora do escopo

O inventário encontrou questões sobre reimportação e associações históricas. Elas podem ser revisitadas se surgirem como problema real, mas não justificam uma reforma acadêmica nesta etapa.

## Próximo passo

Fechar a PR 2.1 e iniciar **2.2 — Extração SIGAA mais robusta**, sem migration e sem alterar o formato atual das matérias.
