-- Leveling module per-guild settings (level-up announcement channel)
CREATE TABLE IF NOT EXISTS leveling_settings (
  bot_id UUID NOT NULL REFERENCES user_bots(bot_id),
  guild_id BIGINT NOT NULL,
  announce_channel_id BIGINT,
  PRIMARY KEY (bot_id, guild_id)
);
