-- Economy module schema
CREATE TABLE IF NOT EXISTS user_economy (
  bot_id UUID NOT NULL REFERENCES user_bots(bot_id),
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  balance BIGINT NOT NULL DEFAULT 0,
  last_daily_claim TIMESTAMPTZ,
  PRIMARY KEY (bot_id, guild_id, user_id)
);
