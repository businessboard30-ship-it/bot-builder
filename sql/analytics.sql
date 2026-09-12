CREATE TABLE IF NOT EXISTS analytics_events (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, event_type TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX IF NOT EXISTS analytics_events_scope_idx ON analytics_events(bot_id, guild_id, created_at);
