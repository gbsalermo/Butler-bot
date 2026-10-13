-- Registro rápido de treino: idempotência por mensagem do Telegram.
-- Permite que mensagens retidas pelo cliente durante conexão instável sejam
-- entregues depois sem duplicar uma série em caso de reentrega do webhook.

ALTER TABLE workout_set_logs ADD COLUMN source_message_id INTEGER;
ALTER TABLE protocol_mass_set_logs ADD COLUMN source_message_id INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS uq_workout_set_source_message
ON workout_set_logs(user_id, source_message_id)
WHERE source_message_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_protocol_mass_set_source_message
ON protocol_mass_set_logs(user_id, source_message_id)
WHERE source_message_id IS NOT NULL;
