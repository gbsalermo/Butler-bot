# Cardápio do Restaurante Universitário (RU)

**Status:** ativo no runtime Cloudflare  
**Leitura:** pública para todos os usuários do Butler  
**Importação v1:** restrita ao proprietário/admin  
**Entrada de importação:** arquivo `.txt`  
**OCR/foto/PDF escaneado:** não executado pelo Butler nesta versão

## Objetivo

Permitir que o cardápio semanal do Restaurante Universitário seja importado uma vez pelo proprietário e consultado por todos os usuários durante a semana, sem cada pessoa precisar cadastrar sua própria cópia.

Exemplos de consulta pública:

```text
qual o almoço hoje?
qual o café amanhã?
janta de quarta?
o que vai ter no RU hoje?
vegetariano amanhã
tem frango hoje no almoço?
quais dias dessa semana tem carne?
```

## Regra de acesso atual

O cardápio é uma fonte compartilhada do Butler:

```text
proprietário/admin
→ importa o TXT semanal
→ Butler salva o cardápio na fonte do proprietário
→ todos os usuários consultam essa mesma fonte
```

Usuários comuns:

- veem `🍽️ RU` no menu `🏠 Cotidiano`;
- podem consultar hoje, semana, refeições, vegetariano, alimentos e histórico;
- não veem a ação `📤 Atualizar cardápio RU` no teclado público;
- mesmo que possuam um teclado antigo em cache ou digitem a frase de importação manualmente, a operação é bloqueada no servidor.

O proprietário recebe o teclado administrativo ao abrir explicitamente `🍽️ RU`, incluindo `📤 Atualizar cardápio RU`.

## Menu público

```text
🏠 Cotidiano
→ 🍽️ RU

🍽️ Cardápio de hoje     📅 Cardápio da semana
🗃️ Cardápios anteriores
⬅️ Voltar ao cotidiano
```

## Menu do proprietário

```text
🍽️ Cardápio de hoje     📅 Cardápio da semana
📤 Atualizar cardápio RU  🗃️ Cardápios anteriores
⬅️ Voltar ao cotidiano
```

## Fluxo de importação do proprietário

1. O cardápio da universidade é convertido para texto.
2. O proprietário abre `🏠 Cotidiano → 🍽️ RU → 📤 Atualizar cardápio RU`.
3. Envia o arquivo `.txt`.
4. O Butler apresenta uma prévia com período, dias e refeições reconhecidas.
5. O proprietário digita `confirmar` para salvar.
6. Se a mesma semana já existir, a nova importação substitui os itens daquela semana.
7. A partir desse momento, todos os usuários consultam o mesmo cardápio.

A confirmação existe para impedir que um TXT mal convertido altere o cardápio silenciosamente.

## Formato TXT recomendado

```text
CARDAPIO RU
SEMANA: 31/08/2026 a 05/09/2026

[SEGUNDA - 31/08/2026]

CAFE
Bebida: Café preto / café com leite / suco
Proteína: Queijo
Pão: Pão / pão integral
Acompanhamento: Mingau de milho
Fruta: Laranja
Vegetariano: Patê de lentilha

ALMOCO
Acompanhamento 01: Feijão carioca
Acompanhamento 02: Arroz temperado
Proteína 01: Ensopado de carne
Proteína 02: Filé de frango acebolado
Guarnição: Macarrão alho e óleo
Salada 01: Repolho
Suco: Suco de frutas
Sobremesa: Melancia
Vegetariano: Bolinho de batata doce com queijo

JANTAR
Bebida: Café preto / café com leite / suco
Pão: Pão / pão integral
Sopa: Sopa de legumes
Entrada: Beterraba com tomate
Acompanhamento: Batata doce
Proteína: Frango em cubos ao molho rosé
Vegetariano: Suflê de legumes

[TERCA - 01/09/2026]
...
```

O parser tolera pequenas variações comuns:

- dia com ou sem colchetes;
- `CAFE`, `CAFÉ`, `CAFÉ DA MANHÃ` ou `DESJEJUM`;
- `ALMOCO`/`ALMOÇO`;
- `JANTAR`/`JANTA`;
- item em `Categoria: valor`;
- item separado por `|`, tabulação ou múltiplos espaços;
- cabeçalho do dia somente pelo nome quando a linha `SEMANA` informa o período.

## Regras de data

- `hoje`: data local atual do Butler;
- `amanhã`: dia seguinte;
- `depois de amanhã`: +2 dias;
- `quarta`, `sexta`, etc.: dia correspondente da semana corrente;
- `quarta que vem` / `próxima quarta`: semana seguinte;
- datas explícitas `dd/mm` ou `dd/mm/aaaa` também podem ser usadas nas consultas.

Se não houver cardápio para a semana consultada, o Butler informa que ainda não recebeu o TXT em vez de inventar uma resposta.

## Persistência

Migration formal:

```text
cloudflare/migrations/0009_ru_menu.sql
```

Tabelas:

```text
ru_menu_imports
- id
- user_id
- week_start
- week_end
- source_filename
- imported_at
- UNIQUE(user_id, week_start)

ru_menu_entries
- id
- user_id
- import_id
- meal_date
- meal_type
- item_label
- item_value
- position
```

O schema continua associado a `user_id`, mas a política atual de produto usa o registro do usuário marcado como `is_owner=1` como fonte pública do RU. Isso preserva o modelo existente e permite reabrir importações individuais no futuro sem migration destrutiva.

O módulo mantém `CREATE TABLE/INDEX IF NOT EXISTS` defensivo apenas quando o domínio RU é utilizado. A migration continua sendo a fonte formal do schema.

## Arquitetura

Parser/persistência do domínio:

```text
cloudflare/src/ru_menu.py
```

Política de acesso e roteamento público:

```text
cloudflare/src/operational_menu.py
```

Fluxo:

```text
entry.py
→ production_usability_patch
→ operational_menu.py
   → resolve usuário solicitante
   → bloqueia importação se não for proprietário
   → resolve o user_id do proprietário como fonte pública
   → ru_menu.handle_message(...)
→ demais fast paths
```

A posição antes dos fast paths genéricos é intencional para que frases como `qual o almoço hoje?` não sejam consumidas por outro domínio.

## Limitações da v1

- somente `.txt` para importação;
- importação restrita ao proprietário/admin;
- limite de 1 MB por arquivo;
- não executa OCR;
- não lê diretamente foto do quadro, print ou PDF escaneado;
- não tenta inferir alimento ausente ou corrigir cardápio incompleto;
- histórico lista as semanas importadas;
- consultas públicas usam a fonte compartilhada do proprietário.

Uma evolução futura pode receber foto/PDF e transformar em texto antes da mesma etapa de prévia/confirmação, sem mudar as consultas públicas.
