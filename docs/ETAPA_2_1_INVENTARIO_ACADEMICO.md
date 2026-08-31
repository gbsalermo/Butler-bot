# Butler — Etapa 2.1: Inventário e autoridades do domínio acadêmico

**Data-base:** 31/08/2026  
**Status:** inventário inicial concluído; consolidação ainda não implementada  
**Etapa anterior:** Etapa 1 concluída

## Objetivo

Mapear o domínio acadêmico que realmente governa produção antes de alterar schema, importação ou experiência de usuário.

A Etapa 2 não deve transformar o problema em uma sequência de novos patches. Primeiro é necessário saber quem lê, quem escreve e qual dado precisa sobreviver a edição/reimportação.

---

## 1. Modelo formal atual

### `subjects`

Definido em `0001_initial.sql`:

```text
id
user_id
name
active
created_at
```

Restrição atual:

```text
UNIQUE(user_id, name)
```

Não existem formalmente ainda:

```text
code
professor
course_load
notes
term/semester
```

### `subject_sessions`

```text
id
subject_id
weekday
start_time
end_time
location
```

Uma matéria já pode possuir múltiplas sessões. Porém não existe `UNIQUE` para impedir duas sessões idênticas.

### Presença/faltas

`0003_attendance.sql` separa:

```text
subject_attendance_settings
subject_absences
```

`subject_absences` referencia:

```text
user_id
subject_id
session_id
class_date
```

com `ON DELETE CASCADE` para matéria/sessão.

Isso significa que identidade estável de matéria e sessão é requisito para preservar histórico.

### Provas

Não há tabela acadêmica própria de avaliações.

Hoje prova é representada em `daily_items`:

```text
kind = compromisso
details = exam:<subject_id>
title = Prova de <matéria>
```

A associação com matéria é textual (`details`), não FK.

---

## 2. Autoridades reais do runtime

### `app.py`

Ainda contém a implementação-base de:

- menu acadêmico;
- adicionar matéria;
- remover matéria;
- trancar matéria;
- parser `parse_schedule_text()`;
- importação PDF/TXT;
- preview/estado `import_confirm`;
- persistência da grade importada.

O parser entende código SIGAA e retorna `code`, mas esse campo não é persistido porque `subjects` não possui coluna correspondente.

### `academic_polish.py`

É instalado no runtime e monkeypatcha:

```text
app.handle_message
app.handle_state
app.agenda_text
```

Na prática, hoje é a autoridade operacional da **edição guiada** de matéria/sessões e também acrescenta o onboarding/guia de importação SIGAA.

Ele permite:

- renomear matéria;
- editar dia;
- editar horário;
- editar sala/local;
- adicionar aula/sessão;
- remover aula/sessão.

Portanto a mensagem-base antiga em `app.py` dizendo que edição ainda não existe não representa o comportamento final após `install()`.

### `academic_intelligence.py`

Governa parte relevante de:

- consultas naturais de agenda acadêmica;
- resolução de matéria por texto;
- próxima aula;
- listagem/criação de provas;
- lembretes de prova;
- menu acadêmico complementar.

Também instala wrapper em `app.scheduled_tick` para `exam_reminders()`.

### `exam_phrase_patch.py`

Fast path natural para criação de prova. Usa `_subject_lookup()` e `_save_exam()` de `academic_intelligence`.

### `exam_cancel_patch.py`

Responsável pelo cancelamento de provas em linguagem/fluxo específico.

### `attendance_patch.py`

É a base da presença/faltas:

- resolução de matéria;
- cálculo de unidades de falta pela duração da sessão;
- gravação idempotente por `user_id + session_id + class_date`;
- relatório básico;
- callback `vou/não vou` original.

Importante: `vou` não salva presença. Só a ausência explícita é persistida.

### `attendance_enhancement.py`

Complementa/monkeypatcha a camada de presença:

- relatório com percentual/alertas;
- callback aprimorado;
- solicitação do limite de faltas;
- `ensure_schema()` defensivo.

O schema formal já existe em migration 0003; o DDL local é compatibilidade operacional, não fonte formal.

### `attendance_management.py`

Governa:

- editar limite;
- excluir/corrigir falta com confirmação;
- listagem de ausências recentes.

### `attendance_production_fix.py`

Governa a entrega temporal de aula/presença:

- aviso T-10;
- aviso no início da aula;
- `notification_log` para idempotência;
- heartbeat do scheduler acadêmico;
- menu acadêmico final instalado em runtime.

### `attendance_alarm.py`

Durable Object de contingência para presença/aulas. Não substitui a autoridade de negócio; rearma/dispara o mesmo fluxo confiável.

---

## 3. Importação atual

### Entrada

O onboarding de `academic_polish.py` recomenda corretamente:

```text
Componente Curricular | Local | Horário
```

Formatos aceitos:

- PDF textual/pesquisável;
- TXT.

Imagem/scan não usa OCR em produção.

### Parser

`app.parse_schedule_text()` procura códigos SIGAA como:

```text
35M45
24M23
2T23
```

E converte para sessões explícitas:

```text
name
weekday
start
end
location
code
```

O parser é relativamente puro e pode servir como primeiro adaptador, mas hoje ainda está dentro de `app.py`.

### Preview

Já existe uma boa decisão que deve ser preservada:

```text
arquivo
→ parse
→ prévia
→ usuário digita confirmar
→ persistência
```

### Persistência atual — problema crítico

Na confirmação da grade, o código executa:

```text
DELETE subject_sessions do usuário
DELETE subjects do usuário
→ INSERT matérias/sessões parseadas
```

Isso não é um merge e não preserva identidade.

---

## 4. Riscos encontrados

### P0 — reimportação pode destruir histórico de faltas

Como `subject_absences.subject_id/session_id` usam `ON DELETE CASCADE`, apagar todas as matérias/sessões pode apagar faltas e configurações acadêmicas relacionadas.

**Decisão para Etapa 2:** importação não pode continuar baseada em `delete all + recreate`.

### P0 — provas podem ficar órfãs semanticamente

Provas usam:

```text
details = exam:<subject_id>
```

Depois de apagar/recriar matérias, os IDs podem mudar. O `daily_item` não é apagado por FK, mas deixa de casar com a nova matéria.

**Decisão:** a associação avaliação ↔ matéria precisa de identidade estável/normalizada antes de consolidar importação.

### P1 — código SIGAA é reconhecido e descartado

O parser já retorna `code`, mas o modelo não salva.

Isso elimina o melhor identificador externo disponível para reconciliar uma matéria importada com a já existente.

### P1 — edição existe por monkeypatch, não no módulo dono

`app.py` mantém um fluxo-base e `academic_polish.py` substitui partes em runtime.

Funciona, mas a autoridade fica difícil de entender/testar. A Etapa 2 deve consolidar gradualmente essa responsabilidade em módulo acadêmico explícito, sem big-bang.

### P1 — sessões podem duplicar

`subject_sessions` não possui unicidade formal para:

```text
subject_id + weekday + start_time + end_time + location
```

Edição/importações incrementais futuras precisam de estratégia de identidade/deduplicação.

### P1 — remoção de matéria é destrutiva

`Remover matéria` executa DELETE; `Trancar matéria` apenas seta `active=0`.

Antes de ampliar o modelo, definir claramente:

```text
trancar → preservar histórico e ocultar do período ativo
remover → quando realmente apagar? arquivar? soft delete?
```

### P2 — menus acadêmicos possuem várias definições

Há menu em `app.py`, `academic_intelligence.py` e `attendance_production_fix.py`; o último instala a versão final.

Não é urgente, mas deve haver uma autoridade clara ao fim da Etapa 2.

### P2 — schema defensivo e heartbeat ainda nascem em runtime

`attendance_enhancement.ensure_schema()` repete migration 0003 e `attendance_production_fix._heartbeat()` cria `attendance_scheduler_ticks` dinamicamente.

A disciplina final deve preferir migration formal para estruturas permanentes.

---

## 5. Autoridades-alvo da Etapa 2

Sem implementar tudo de uma vez, a direção é:

```text
academic_model / repository
→ matéria + sessões + identidade acadêmica

academic_import
→ adaptadores (SIGAA primeiro)
→ preview normalizado
→ merge plan
→ confirmação
→ persistência

academic_ui
→ cadastro/edição/trancar/arquivar

academic_assessments
→ provas/avaliações/trabalhos associados por identidade estável

attendance
→ continua responsável por faltas/presença explícita

academic_scheduler
→ aula + avisos temporais, reaproveitando idempotência atual
```

Nomes finais dos módulos podem aproveitar os arquivos existentes; não criar todos como patches novos por padrão.

---

## 6. Ordem proposta dentro da Etapa 2

### 2.1 Inventário/autoridade

- [x] schema atual mapeado;
- [x] CRUD atual mapeado;
- [x] importação atual mapeada;
- [x] edição por monkeypatch identificada;
- [x] presença/faltas mapeadas;
- [x] provas mapeadas;
- [x] riscos de reimportação identificados;
- [ ] adicionar regressões de caracterização do parser/fluxos críticos;
- [ ] registrar correção documental da migration 0009;
- [ ] fechar PR 2.1.

### 2.2 Identidade/modelo acadêmico

Antes de migration, definir:

- campos de `subjects`;
- identidade interna estável;
- `external_code`/código SIGAA;
- período/semestre se necessário;
- política de trancar/arquivar/remover;
- unicidade de sessões;
- associação de avaliações.

### 2.3 Migration + backfill

Somente depois do desenho 2.2 aprovado.

### 2.4 Importador normalizado

Extrair parser SIGAA de `app.py`, gerar estrutura normalizada e um plano de merge sem escrita.

### 2.5 Preview de diferenças

Exibir algo como:

```text
+ matéria nova
~ horário alterado
= matéria mantida
- sessão ausente na nova grade (confirmar ação)
```

### 2.6 Persistência/merge confirmado

Aplicar somente depois da confirmação, preservando IDs/histórico quando a matéria é a mesma.

### 2.7 Onboarding/documentação

Alinhar primeiro acesso, menu acadêmico, README e exemplos SIGAA.

---

## 7. Invariantes para não quebrar

- aula prevista nunca implica presença;
- `vou` não grava presença fictícia;
- falta só por ação explícita;
- reimportação não apaga histórico acadêmico silenciosamente;
- importação sempre tem preview;
- scan/imagem não é aceito como PDF textual;
- dados de um usuário nunca entram na grade de outro;
- provas existentes não podem perder matéria silenciosamente;
- CI verde não prova deploy Cloudflare.

---

## Próximo passo

Fechar a 2.1 com testes de caracterização e então desenhar **2.2 — identidade/modelo acadêmico**, antes de criar qualquer migration nova.
