CREATE TABLE IF NOT EXISTS autopost_feeds (bot_id UUID NOT NULL REFERENCES user_bots(bot_id), id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, feed_url TEXT NOT NULL, channel_id BIGINT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE, last_title TEXT);
ALTER TABLE autopost_feeds ADD COLUMN IF NOT EXISTS last_item_key TEXT;
ALTER TABLE autopost_feeds ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE autopost_feeds ADD COLUMN IF NOT EXISTS last_error TEXT;
CREATE INDEX IF NOT EXISTS autopost_feeds_scope_idx ON autopost_feeds(bot_id,guild_id,enabled);
