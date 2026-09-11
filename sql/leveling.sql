-- Leveling module schema
CREATE TABLE IF NOT EXISTS user_levels (guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, xp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 0, last_xp_gain TIMESTAMPTZ, PRIMARY KEY (guild_id, user_id));
