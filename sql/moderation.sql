-- Moderation module schema
CREATE TABLE IF NOT EXISTS mod_warnings (id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, moderator_id BIGINT NOT NULL, reason TEXT NOT NULL, timestamp TIMESTAMPTZ NOT NULL);
CREATE INDEX IF NOT EXISTS mod_warnings_user_idx ON mod_warnings(guild_id, user_id);
