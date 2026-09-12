CREATE TABLE IF NOT EXISTS scheduled_messages (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, channel_id BIGINT NOT NULL, message TEXT NOT NULL, status TEXT NOT NULL, run_at TIMESTAMPTZ, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
ALTER TABLE scheduled_messages ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE scheduled_messages ADD COLUMN IF NOT EXISTS last_error TEXT;
CREATE INDEX IF NOT EXISTS scheduled_messages_scope_idx ON scheduled_messages(bot_id,guild_id,status,run_at);
