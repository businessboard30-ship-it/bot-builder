CREATE TABLE IF NOT EXISTS tickets (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, channel_id BIGINT, opener_id BIGINT NOT NULL, subject TEXT NOT NULL, status TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS channel_id BIGINT;
CREATE INDEX IF NOT EXISTS tickets_scope_idx ON tickets(bot_id,guild_id,status);
