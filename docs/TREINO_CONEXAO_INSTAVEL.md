# Butler — experiência de musculação e conexão instável

## Registro rápido

A entrada padrão por mensagem autossuficiente é:

```text
Supino reto | 40 kg | 12 reps
Supino reto | 45 kg | 10 reps
Supino reto | 50 kg | 8 reps
```

Cada mensagem tem exercício, carga e repetições completos. O nome precisa ser igual
ao da ficha do dia; dados inválidos não são gravados. O registro rápido é processado
antes dos fluxos guiados, e a confirmação é enviada somente após o banco reconhecer
a mensagem. A migration `0016_workout_quick_log.sql` adiciona o identificador de
origem e índices únicos ao histórico para proteger contra reentrega do Telegram.

A data usada é a da mensagem original no Telegram, e não a data da conexão de volta.
Se a mensagem não chegar ao Telegram, não há fila local sob controle do Worker:
não se trata de suporte totalmente offline.

## Menu contextual enxuto

```text
🏋️ Treino
📅 Treino de hoje           🗓️ Escolher dia
📆 Ver semanas             📝 Registrar série
📈 Progresso               ⚙️ Mais opções
⬅️ Início
```

Para o dono com protocolo ainda não iniciado, aparece adicionalmente
`🚀 Começar os trabalhos`. Depois de iniciar, o botão desaparece.

O objetivo é não apresentar simultaneamente todas as funcionalidades:

- `🗓️ Escolher dia`: submenu com **amanhã e os sete dias da semana**;
- `📆 Ver semanas`: submenu com **semana completa e próximas semanas**;
- `⚙️ Mais opções`: finalizar/registrar ausência do dia, histórico de cargas,
  substituição de exercício, importação e gestão do protocolo;
- ações de gestão: com protocolo ativo, `⏹️ Encerrar trabalhos` e
  `🔄 Reiniciar os trabalhos`; após encerramento, somente reinício.

Após registrar uma série pelo assistente guiado, o teclado também volta para
o menu compacto. Os comandos digitados `treino de amanhã`, `treino de sexta`,
`semana 2` continuam funcionando independentemente dos submenus.

Encerrar preserva histórico e exige confirmação `ENCERRAR`. Reiniciar volta à
semana 1 e apaga registros do perfil **apenas** após `APAGAR TREINOS`.
Cancelar não altera o banco. `✅ Finalizar treino` trata somente o dia atual,
e não encerra o protocolo.

## Consulta por dia e por semana

- `📅 Treino de amanhã` no submenu Escolher dia abre somente a ficha de amanhã;
- `🗓️ Escolher dia` permite tocar em Segunda, Terça, Quarta, Quinta, Sexta,
  Sábado ou Domingo, ou digitar o dia enquanto o seletor estiver aberto;
- comandos livres e explícitos também funcionam: `treino de amanhã`,
  `treino de sexta`, `qual o treino de sábado?`;
- dias da semana usam a próxima ocorrência, incluindo o dia de hoje quando
  coincidir; a resposta informa a data calculada;
- `amanhã`, `sexta` ou `sábado` sem contexto de treino **não**
  sequestram os fluxos de agenda; só são usados como resposta quando a escolha
  de dia estiver aberta;
- consultas de dias futuros exibem a ficha planejada, não fingem séries
  registradas e não avançam o protocolo;
- `📆 Ver semanas → 🗓️ Semana completa` mostra os sete dias (inclusive sem treino);
- `📆 Ver semanas → 📆 Próximas semanas` lista as semanas seguintes do protocolo;
- `📆 Semana 2` ou `semana 2` abre a ficha completa da semana escolhida;
- consultar semanas futuras não muda `current_week` e não registra progresso.

O perfil genérico mantém a própria divisão semanal, sem acesso ao protocolo
pessoal. A progressão automática entre semanas **não** foi adicionada: a semana
atual permanece determinada pelo estado já existente, sem avanços silenciosos.

## Validação e deploy

- `python -m compileall -q src`
- `pytest -q`
- conferir aplicação da migration 0016 no D1 correto;
- validar webhook/deploy do Worker `salbutler-bot` separadamente;
- testar no Telegram real com 2 séries distintas, 1 reenvio, menu antes/depois
  de iniciar e consulta de semana futura.

**CI verde não significa deploy executado.**
