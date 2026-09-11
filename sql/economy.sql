-- Economy module schema
CREATE TABLE IF NOT EXISTS user_economy (guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, balance BIGINT NOT NULL DEFAULT 0, last_daily_claim TIMESTAMPTZ, PRIMARY KEY (guild_id, user_id));
