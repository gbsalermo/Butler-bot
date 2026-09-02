# Etapa 11 — Idiomas e internacionalização

**Status:** ⏳ planejada  
**Posição:** última etapa do roadmap oficial, depois da Etapa 10 — Abertura pública, capacidade e escala  
**Objetivo:** permitir que cada usuário escolha a linguagem do Butler, começando por Português do Brasil, Inglês e Espanhol, sem alterar nem traduzir automaticamente os dados pessoais já cadastrados.

## Escopo inicial

Idiomas suportados no primeiro gate:

- 🇧🇷 Português do Brasil (`pt-BR`) — padrão atual;
- 🇺🇸 Inglês (`en`);
- 🇪🇸 Espanhol (`es`).

A arquitetura deve permitir adicionar outros idiomas posteriormente sem duplicar handlers ou regras de negócio.

## Experiência esperada

O usuário poderá trocar o idioma nas configurações do Butler a qualquer momento. A preferência será persistida por usuário e aplicada nas interações seguintes.

A troca deve abranger:

- menus e botões;
- mensagens de confirmação e erro;
- textos de ajuda e onboarding;
- respostas operacionais;
- lembretes, resumos e notificações;
- Cursos, Modo Estudo, agenda, tarefas, rotinas e demais áreas já existentes;
- formatação textual de datas e horários quando houver diferença de idioma/locale.

## Regras obrigatórias

1. A preferência de idioma é individual por usuário.
2. Português do Brasil permanece como idioma padrão quando nenhuma preferência estiver salva.
3. Trocar a linguagem da interface não traduz automaticamente títulos, tarefas, matérias, cursos, notas ou qualquer conteúdo escrito pelo usuário.
4. Regras de negócio, IDs, estados e persistência não podem depender do texto traduzido de botões.
5. Ações equivalentes devem usar identificadores semânticos internos, evitando três versões paralelas da mesma lógica.
6. Nenhum idioma pode alterar as garantias atuais de segurança, isolamento por usuário ou progresso explícito.
7. Fluxos críticos não devem misturar idiomas por falta de tradução.
8. Uma chave de tradução ausente deve possuir fallback controlado e observável.
9. Comandos e linguagem natural devem reconhecer a intenção no idioma selecionado sem autorizar escrita apenas por reconhecimento textual.
10. A mudança de idioma deve poder ser revertida a qualquer momento.

## Preparação técnica esperada

Antes de traduzir textos em massa:

- inventariar strings operacionais e textos de UI;
- separar texto de apresentação da regra de negócio;
- criar catálogo/chaves de tradução;
- persistir `locale` ou equivalente por usuário;
- desacoplar handlers que hoje dependam do texto exato de botões;
- definir helpers de tradução e formatação;
- manter uma única autoridade de domínio para cada área.

## Gate final da Etapa 11

A etapa só termina quando:

- o usuário consegue alternar entre `pt-BR`, `en` e `es` sem perder contexto ou dados;
- menus e principais fluxos operacionais funcionam nos três idiomas;
- tarefas, rotinas, agenda, Modo Estudo e Cursos passam por regressão nos três idiomas;
- notificações e erros respeitam a preferência persistida;
- conteúdo escrito pelo usuário permanece intacto ao mudar o idioma;
- não existe dependência crítica de regras de negócio em labels traduzidas;
- testes garantem isolamento da preferência por usuário;
- documentação e manual explicam como trocar o idioma;
- CI permanece verde;
- deploy Cloudflare é validado separadamente.

## Fora do escopo inicial

- tradução automática de conteúdo do usuário;
- tradução de arquivos importados;
- escolha automática de idioma por localização geográfica;
- novos idiomas além de Português do Brasil, Inglês e Espanhol;
- uso de LLM apenas para traduzir mensagens de sistema em tempo real.

A internacionalização deve ser determinística para a interface e os fluxos operacionais. Recursos de IA continuam sujeitos à trilha pós-roadmap e ao gate de estabilidade correspondente.
