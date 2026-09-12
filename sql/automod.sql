CREATE TABLE IF NOT EXISTS automod_settings (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), guild_id BIGINT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE, blocked_words JSONB NOT NULL DEFAULT '[]'::jsonb, violation_window_minutes INTEGER NOT NULL DEFAULT 10, timeout_threshold INTEGER NOT NULL DEFAULT 3, kick_threshold INTEGER NOT NULL DEFAULT 5, ban_threshold INTEGER NOT NULL DEFAULT 7, PRIMARY KEY (bot_id,guild_id));
ALTER TABLE automod_settings ADD COLUMN IF NOT EXISTS violation_window_minutes INTEGER NOT NULL DEFAULT 10;
ALTER TABLE automod_settings ADD COLUMN IF NOT EXISTS timeout_threshold INTEGER NOT NULL DEFAULT 3;
ALTER TABLE automod_settings ADD COLUMN IF NOT EXISTS kick_threshold INTEGER NOT NULL DEFAULT 5;
ALTER TABLE automod_settings ADD COLUMN IF NOT EXISTS ban_threshold INTEGER NOT NULL DEFAULT 7;
CREATE TABLE IF NOT EXISTS automod_violations (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, reason TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX IF NOT EXISTS automod_violations_scope_idx ON automod_violations(bot_id,guild_id,user_id,created_at);
