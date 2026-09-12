CREATE TABLE IF NOT EXISTS giveaways (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, channel_id BIGINT NOT NULL, message_id BIGINT, host_id BIGINT NOT NULL, prize TEXT NOT NULL, status TEXT NOT NULL, ends_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS giveaway_entries (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), giveaway_id BIGINT NOT NULL REFERENCES giveaways(id) ON DELETE CASCADE, user_id BIGINT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), PRIMARY KEY (bot_id, giveaway_id, user_id));
ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS channel_id BIGINT;
ALTER TABLE giveaways ADD COLUMN IF NOT EXISTS message_id BIGINT;
CREATE INDEX IF NOT EXISTS giveaways_scope_idx ON giveaways(bot_id,guild_id,status);
