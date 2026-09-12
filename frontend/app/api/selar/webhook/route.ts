/**
 * Intentionally inactive compatibility stub.
 *
 * Selar currently provides no webhook delivery, so nothing in production calls
 * this route. The live unlock flow starts at the landing page's "I've Paid"
 * submission and requires manual Discord approval; this handler never unlocks
 * a bot. Keep it only as a guarded placeholder if Selar adds webhooks later.
 */
import { NextRequest, NextResponse } from 'next/server'
import { getUnlockPool } from '@/lib/server-db'

const PRODUCT_CODE = 'bot-builder-unlock'
const EXPECTED_AMOUNT = 500

function constantTimeEqual(left: string, right: string) {
  if (left.length !== right.length) return false
  let result = 0
  for (let index = 0; index < left.length; index += 1) result |= left.charCodeAt(index) ^ right.charCodeAt(index)
  return result === 0
}

export async function POST(request: NextRequest) {
  const configuredSecret = process.env.SELAR_WEBHOOK_SECRET
  const suppliedSecret = request.headers.get('x-selar-webhook-secret') ?? ''
  if (!configuredSecret || !constantTimeEqual(suppliedSecret, configuredSecret)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  let payload: Record<string, unknown>
  try {
    payload = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const reference = String(payload.reference ?? payload.order_reference ?? '').trim()
  const eventId = String(payload.event_id ?? payload.id ?? '').trim()
  const productCode = String(payload.product_code ?? payload.product ?? '').trim()
  const status = String(payload.status ?? '').toLowerCase()
  const amount = Number(payload.amount_cents ?? (Number(payload.amount) * 100))
  const currency = String(payload.currency ?? 'USD').toUpperCase()

  if (!reference || !eventId || productCode !== PRODUCT_CODE || amount !== EXPECTED_AMOUNT || currency !== 'USD') {
    return NextResponse.json({ error: 'Payment payload rejected' }, { status: 422 })
  }

  const nextStatus = ['paid', 'successful', 'completed', 'verified'].includes(status) ? 'verified' : 'rejected'
  const pool = getUnlockPool()
  const client = await pool.connect()
  try {
    await client.query('BEGIN')
    const payment = await client.query(
      `INSERT INTO unlock_payments (reference, product_code, amount_cents, currency, status, buyer_email, provider_event_id, verified_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, CASE WHEN $5 = 'verified' THEN NOW() ELSE NULL END)
       ON CONFLICT (reference) DO UPDATE SET status = CASE WHEN unlock_payments.status = 'verified' THEN 'verified' ELSE EXCLUDED.status END,
       buyer_email = COALESCE(EXCLUDED.buyer_email, unlock_payments.buyer_email), provider_event_id = COALESCE(unlock_payments.provider_event_id, EXCLUDED.provider_event_id),
       verified_at = CASE WHEN unlock_payments.status = 'verified' OR EXCLUDED.status = 'verified' THEN COALESCE(unlock_payments.verified_at, NOW()) ELSE unlock_payments.verified_at END,
       updated_at = NOW() RETURNING id`,
      [reference, PRODUCT_CODE, EXPECTED_AMOUNT, 'USD', nextStatus, typeof payload.email === 'string' ? payload.email : null, eventId],
    )
    await client.query(
      `INSERT INTO unlock_payment_events (payment_id, provider_event_id, event_type, payload)
       VALUES ($1, $2, $3, $4) ON CONFLICT (provider_event_id) DO NOTHING`,
      [payment.rows[0].id, eventId, status || 'unknown', payload],
    )
    await client.query('COMMIT')
    return NextResponse.json({ accepted: true })
  } catch {
    await client.query('ROLLBACK')
    return NextResponse.json({ error: 'Unable to record payment' }, { status: 500 })
  } finally {
    client.release()
  }
}
