-- === LEVELING TABLES ===
CREATE TABLE IF NOT EXISTS user_levels (
  guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, xp INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 0, last_xp_gain TIMESTAMPTZ,
  PRIMARY KEY (guild_id, user_id)
);

-- === WELCOME TABLES ===
CREATE TABLE IF NOT EXISTS welcome_settings (
  guild_id BIGINT PRIMARY KEY, channel_id BIGINT NOT NULL,
  message_template TEXT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE
);

-- === MODERATION TABLES ===
CREATE TABLE IF NOT EXISTS mod_warnings (
  id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL,
  moderator_id BIGINT NOT NULL, reason TEXT NOT NULL, timestamp TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS mod_warnings_user_idx ON mod_warnings(guild_id, user_id);

-- === WIZARD TABLES ===
CREATE TABLE IF NOT EXISTS wizard_sessions (
  user_id BIGINT PRIMARY KEY, current_step INTEGER NOT NULL DEFAULT 1,
  answers JSONB NOT NULL DEFAULT '{}'::jsonb, started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'completed'))
);
CREATE INDEX IF NOT EXISTS wizard_sessions_expiry_idx ON wizard_sessions(status, expires_at);

-- === USER BOTS TABLES ===
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS user_bots (
  user_id BIGINT NOT NULL, bot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), bot_name TEXT NOT NULL,
  modules_enabled JSONB NOT NULL DEFAULT '[]'::jsonb, encrypted_token TEXT NOT NULL,
  currency_name TEXT NOT NULL DEFAULT 'coins', prefix TEXT NOT NULL DEFAULT '!',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), last_regenerated_at TIMESTAMPTZ,
  module_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
  module_schema_hashes JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS user_bots_user_idx ON user_bots(user_id);
CREATE INDEX IF NOT EXISTS user_bots_created_idx ON user_bots(user_id, created_at);

-- === ECONOMY TABLES ===
CREATE TABLE IF NOT EXISTS user_economy (
  guild_id BIGINT NOT NULL, user_id BIGINT NOT NULL, balance BIGINT NOT NULL DEFAULT 0,
  last_daily_claim TIMESTAMPTZ,
  PRIMARY KEY (guild_id, user_id)
);
