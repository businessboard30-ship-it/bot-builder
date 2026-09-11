-- Welcome module schema
CREATE TABLE IF NOT EXISTS welcome_settings (guild_id BIGINT PRIMARY KEY, channel_id BIGINT NOT NULL, message_template TEXT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE);
