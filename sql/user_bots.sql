-- Generated bots owned by users. The maximum of three is enforced by commands/build.py.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
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
  module_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
  module_schema_hashes JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS user_bots_user_idx ON user_bots(user_id);
CREATE INDEX IF NOT EXISTS user_bots_created_idx ON user_bots(user_id, created_at);
