CREATE TABLE IF NOT EXISTS unlock_payments (
  id BIGSERIAL PRIMARY KEY,
  reference TEXT NOT NULL UNIQUE,
  product_code TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK (amount_cents = 500),
  currency TEXT NOT NULL CHECK (currency = 'USD'),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'verified', 'rejected', 'expired')),
  buyer_email TEXT,
  provider_event_id TEXT UNIQUE,
  verified_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  submitted_at TIMESTAMPTZ,
  notified_at TIMESTAMPTZ,
  approved_by TEXT,
  bot_id UUID,
  buyer_name TEXT,
  review_message_id TEXT
);

CREATE TABLE IF NOT EXISTS unlock_payment_events (
  id BIGSERIAL PRIMARY KEY,
  payment_id BIGINT REFERENCES unlock_payments(id) ON DELETE CASCADE,
  provider_event_id TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS unlock_payments_status_idx ON unlock_payments(status);
CREATE INDEX IF NOT EXISTS unlock_payment_events_payment_idx ON unlock_payment_events(payment_id);
