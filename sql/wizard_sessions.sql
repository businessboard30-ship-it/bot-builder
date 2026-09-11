-- Requires pgcrypto for gen_random_uuid().
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- In-progress Bot Builder wizard sessions.
CREATE TABLE IF NOT EXISTS wizard_sessions (
  user_id BIGINT PRIMARY KEY,
  current_step INTEGER NOT NULL DEFAULT 1,
  answers JSONB NOT NULL DEFAULT '{}'::jsonb,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'completed'))
);
CREATE INDEX IF NOT EXISTS wizard_sessions_expiry_idx ON wizard_sessions(status, expires_at);

-- Generated bot records. The three-bot limit is enforced by the command layer.
CREATE TABLE IF NOT EXISTS user_bots (
  user_id BIGINT NOT NULL,
  bot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bot_name TEXT NOT NULL,
  modules_enabled JSONB NOT NULL DEFAULT '[]'::jsonb,
  encrypted_token TEXT NOT NULL,
  currency_name TEXT NOT NULL DEFAULT 'coins',
  prefix TEXT NOT NULL DEFAULT '!',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_regenerated_at TIMESTAMPTZ,
  module_versions JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS user_bots_user_idx ON user_bots(user_id);
CREATE INDEX IF NOT EXISTS user_bots_created_idx ON user_bots(user_id, created_at);
