# Butler — Etapa 2: Importação acadêmica confiável

**Data-base:** 31/08/2026  
**Status:** escopo corrigido após validação do produto

## Decisão de produto

O modelo acadêmico atual já atende bem e **não será reformulado nesta etapa**.

Objetivo da Etapa 2:

> aumentar a confiança na extração e no cadastro inicial das matérias de novos usuários.

Fora do escopo, salvo bug mínimo aprovado:

- redesenhar `subjects` / `subject_sessions`;
- adicionar professor, carga horária, semestre ou observações;
- criar novo modelo de avaliações/trabalhos;
- refatorar presença/faltas;
- alterar a edição manual atual;
- criar migration acadêmica por melhoria arquitetural.

## Formato preservado

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

## Fonte recomendada

Tabela do painel principal do SIGAA:

```text
Componente Curricular | Local | Horário
```

Aceitar PDF textual/pesquisável e TXT. Sem OCR em produção.

## 2.1 — Caracterização do importador atual ✅

Os testes já protegem:

- múltiplos dias do mesmo código;
- blocos M/T/N;
- localização opcional;
- falsos positivos básicos;
- fonte SIGAA recomendada;
- PDF/TXT e ausência de OCR.

## 2.2 — Extração SIGAA mais robusta

Melhorar espaços/quebras de linha, locais, códigos com múltiplos dias, combinações M/T/N, cabeçalhos/rodapés e texto repetido pelo PDF.

Sem alterar o modelo persistido.

## 2.3 — Validação e confiança

Classificar cada bloco:

```text
✅ reconhecido
⚠️ precisa conferir
❌ não reconhecido
```

Evitar nome vazio, horário impossível, duplicata, código parcialmente reconhecido e linha ambígua.

## 2.4 — Prévia clara

Mostrar exatamente matéria, dias, horários e local que serão cadastrados, além de qualquer trecho ambíguo/rejeitado.

## 2.5 — Cadastro inicial seguro

Após confirmação:

- salvar apenas o que apareceu na prévia;
- manter `subjects` + `subject_sessions` como hoje;
- evitar duplicatas internas;
- manter isolamento por usuário;
- não salvar bloco ambíguo/rejeitado.

Foco oficial: **novo usuário / primeira grade**.

Reimportação de grade existente não é objetivo desta etapa.

## 2.6 — Onboarding + regressão real

Explicar onde obter a grade no SIGAA, formato recomendado, PDF/TXT, ausência de OCR, prévia antes de salvar e cadastro manual como alternativa.

## Gate de saída

- [ ] principais variações reais do SIGAA reconhecidas com segurança;
- [ ] múltiplos dias/horários corretos;
- [ ] cabeçalhos/rodapés/linhas irrelevantes ignorados;
- [ ] duplicatas internas eliminadas;
- [ ] ambiguidades sinalizadas;
- [ ] prévia clara;
- [ ] nada salvo antes de confirmação;
- [ ] mesmo modelo acadêmico atual no cadastro final;
- [ ] onboarding validado;
- [ ] cadastro manual preservado;
- [ ] isolamento multiusuário;
- [ ] regressão completa verde.

**Não é requisito da Etapa 2 modificar o schema acadêmico atual.**

## Próximo passo

Fechar a 2.1 e iniciar **2.2 — Extração SIGAA mais robusta**.
