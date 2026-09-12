-- Welcome module schema
CREATE TABLE IF NOT EXISTS welcome_settings (
  bot_id UUID NOT NULL REFERENCES user_bots(bot_id),
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_template TEXT NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (bot_id, guild_id)
);
ALTER TABLE welcome_settings ADD COLUMN IF NOT EXISTS bot_id UUID REFERENCES user_bots(bot_id);
