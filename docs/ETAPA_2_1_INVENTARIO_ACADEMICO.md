# Butler — Etapa 2: Importação acadêmica confiável

**Data-base:** 31/08/2026  
**Status:** escopo corrigido após validação do produto

## Decisão de produto

O modelo acadêmico atual já atende bem e **não será reformulado nesta etapa**.

Objetivo:

> aumentar a confiança na extração e no cadastro inicial das matérias de novos usuários.

Fora do escopo: redesenhar `subjects`/`subject_sessions`, adicionar novos campos acadêmicos, refatorar presença/faltas, criar novo modelo de avaliações/trabalhos ou migration acadêmica por melhoria arquitetural.

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

Painel principal do SIGAA:

```text
Componente Curricular | Local | Horário
```

Aceitar PDF textual/pesquisável e TXT. Sem OCR em produção.

## 2.1 — Caracterização atual ✅

Testes protegem múltiplos dias, blocos M/T/N, localização opcional, falsos positivos básicos, fonte SIGAA recomendada e formatos aceitos.

## 2.2 — Extração mais robusta

Melhorar espaços/quebras de linha, locais, códigos de múltiplos dias, combinações M/T/N, cabeçalhos/rodapés e texto repetido pelo PDF, sem alterar o modelo persistido.

## 2.3 — Validação/confiança

Classificar cada bloco:

```text
✅ reconhecido
⚠️ precisa conferir
❌ não reconhecido
```

Evitar nome vazio, horário impossível, duplicata, código parcialmente reconhecido e linha ambígua.

## 2.4 — Prévia clara

Mostrar matéria, dias, horários e local que serão cadastrados e destacar trechos ambíguos/rejeitados.

## 2.5 — Cadastro inicial seguro

Após confirmação, salvar apenas o que apareceu na prévia, manter o modelo atual, evitar duplicatas internas, manter isolamento por usuário e não salvar bloco ambíguo.

Foco: **novo usuário / primeira grade**. Reimportação não é objetivo desta etapa.

## 2.6 — Onboarding + regressão real

Explicar onde obter a grade, formato recomendado, PDF/TXT, ausência de OCR, prévia antes de salvar e cadastro manual como alternativa.

## Gate

- [ ] principais variações reais reconhecidas com segurança;
- [ ] múltiplos dias/horários corretos;
- [ ] linhas irrelevantes ignoradas;
- [ ] duplicatas internas eliminadas;
- [ ] ambiguidades sinalizadas;
- [ ] prévia clara;
- [ ] nada salvo antes da confirmação;
- [ ] cadastro final usa o modelo atual;
- [ ] onboarding validado;
- [ ] cadastro manual preservado;
- [ ] isolamento multiusuário;
- [ ] regressão verde.

**Não é requisito modificar o schema acadêmico atual.**

## Próximo passo

Fechar 2.1 e iniciar **2.2 — Extração SIGAA mais robusta**.
