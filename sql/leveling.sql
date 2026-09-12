-- Leveling module schema
CREATE TABLE IF NOT EXISTS user_levels (
  bot_id UUID NOT NULL REFERENCES user_bots(bot_id),
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 0,
  last_xp_gain TIMESTAMPTZ,
  PRIMARY KEY (bot_id, guild_id, user_id)
);
