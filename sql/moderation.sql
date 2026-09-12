-- Moderation module schema
CREATE TABLE IF NOT EXISTS mod_warnings (
  id BIGSERIAL PRIMARY KEY,
  bot_id UUID REFERENCES user_bots(bot_id),
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  moderator_id BIGINT NOT NULL,
  reason TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL
);
ALTER TABLE mod_warnings ADD COLUMN IF NOT EXISTS bot_id UUID REFERENCES user_bots(bot_id);
CREATE INDEX IF NOT EXISTS mod_warnings_user_idx
  ON mod_warnings(bot_id, guild_id, user_id);
