# Butler — Etapa 2: Gate final da importação acadêmica confiável

**Data-base:** 31/08/2026  
**Status:** concluída tecnicamente; aguardando merge/pós-merge  
**Escopo confirmado:** confiança da primeira importação acadêmica, sem reformular o modelo atual

## Objetivo

A Etapa 2 foi deliberadamente reduzida ao problema real do produto: aumentar a confiança com que um **novo usuário** envia sua grade do SIGAA e o Butler extrai, mostra e cadastra suas matérias.

O modelo acadêmico atual continua sendo o contrato:

```text
subjects
→ id, user_id, name, active

subject_sessions
→ subject_id, weekday, start_time, end_time, location
```

Não foram adicionados professor, carga horária, semestre, novas tabelas acadêmicas ou migration.

## Fluxo final

```text
novo usuário sem matérias
→ PDF textual/pesquisável ou TXT
→ extração de texto existente
→ academic_import.parse_schedule_report()
→ normalização/validação/deduplicação
→ prévia
→ confiança alta + zero issues
   → confirmação explícita
   → subjects + subject_sessions atuais
→ qualquer issue
   → zero persistência
   → mostrar trecho e motivo
   → pedir outro arquivo/cadastro manual
```

Usuários que já possuem matérias não são assumidos pelo novo fluxo; o comportamento acadêmico existente permanece.

## O que o importador reconhece

- código SIGAA como `35M45`, `24M23`, `2T23`;
- múltiplos dias no mesmo código;
- múltiplos códigos na mesma matéria;
- blocos M/T/N já utilizados pelo Butler;
- nome, horário e local no mesmo registro;
- nome quebrado em duas linhas;
- ordem vertical comum `matéria → local → horário`;
- local na linha posterior ao código;
- local ausente, porque o modelo atual permite `NULL`;
- cabeçalhos/rodapés comuns do SIGAA/PDF;
- linhas duplicadas geradas pela extração de PDF.

## Política de confiança

### Alta

Existe ao menos uma matéria/sessão e **nenhum trecho suspeito**.

Resultado: prévia + botão `✅ Confirmar importação`.

### Média

Há itens seguros, mas também existe trecho acadêmico ambíguo/inválido.

Resultado: o Butler mostra o que conseguiu entender e o trecho que precisa de revisão, mas **não salva nada**.

### Baixa

Nenhum registro acadêmico seguro foi reconhecido.

Resultado: orientar novamente para a fonte recomendada e não persistir.

## Casos que bloqueiam o cadastro

- código SIGAA malformado;
- turno/bloco inexistente;
- blocos repetidos, invertidos ou não contíguos;
- código sem nome de matéria confiável;
- trecho final com aparência de conteúdo acadêmico sem horário reconhecível;
- estrutura que o parser não consegue reconstruir conservadoramente.

A regra é proposital:

```text
melhor pedir conferência
que cadastrar uma grade incompleta como se estivesse certa
```

## Persistência

O primeiro cadastro não apaga grade anterior porque o fluxo só entra quando `subjects` está vazio.

Antes da confirmação o Butler revalida que a grade continua vazia, protegendo duplo envio/concorrência.

A persistência reutiliza somente:

```text
subjects
subject_sessions
```

Se houver erro no meio da primeira gravação, os `subject_id` criados naquela tentativa são removidos em rollback best-effort.

## Onboarding preservado

Fonte recomendada:

```text
Componente Curricular | Local | Horário
```

Formatos:

- PDF com texto pesquisável/selecionável;
- `.txt`.

Sem OCR em produção para print/foto/PDF escaneado.

## Regressões

`cloudflare/tests/test_stage2_academic_import_reliability.py` cobre:

- registro SIGAA em uma linha;
- PDF com colunas quebradas;
- local antes/depois do horário;
- nome quebrado;
- duplicatas;
- múltiplos códigos;
- local opcional;
- código inválido;
- blocos não contíguos;
- falso positivo em texto comum;
- ruído de cabeçalho/rodapé;
- preview seguro × revisão;
- persistência nas tabelas atuais;
- ausência de migration/schema novo;
- instalação do fluxo no runtime.

Primeiro gate da PR #30: **302 testes passando**.

## Gate de saída

- [x] modelo acadêmico atual preservado;
- [x] nenhuma migration acadêmica criada;
- [x] parser do primeiro acesso endurecido;
- [x] quebras comuns de PDF tratadas conservadoramente;
- [x] duplicatas eliminadas;
- [x] horários SIGAA validados;
- [x] baixa/média confiança não grava;
- [x] prévia obrigatória;
- [x] confirmação explícita;
- [x] primeiro cadastro usa somente `subjects` + `subject_sessions`;
- [x] usuário com grade existente não é sequestrado pelo novo fluxo;
- [x] isolamento por `user_id` mantido;
- [x] onboarding SIGAA atual preservado;
- [x] regressão completa da PR verde;
- [ ] merge da PR #30;
- [ ] regressão pós-merge da `main` verde;
- [ ] `STATUS_ATUAL`/Trilha apontando Etapa 3.

## Próxima etapa

Após o fechamento dos três últimos gates: **Etapa 3 — Auxiliares de Tempo / Modo Estudo**.
