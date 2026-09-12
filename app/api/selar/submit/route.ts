import { NextRequest, NextResponse } from 'next/server'
import { getUnlockPool } from '@/lib/server-db'

const REFERENCE = /^[A-Za-z0-9._:-]{6,160}$/

export async function POST(request: NextRequest) {
  let body: { reference?: unknown; bot_id?: unknown; buyer_email?: unknown; buyer_name?: unknown }
  try { body = await request.json() } catch { return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 }) }
  const reference = String(body.reference ?? '').trim()
  const botId = String(body.bot_id ?? '').trim()
  const buyerEmail = String(body.buyer_email ?? '').trim().slice(0, 320)
  const buyerName = String(body.buyer_name ?? '').trim().slice(0, 120)
  if (!REFERENCE.test(reference) || !/^[0-9a-f-]{36}$/i.test(botId)) return NextResponse.json({ error: 'Invalid payment target' }, { status: 400 })

  // Single-use expiry prevents duplicate review noise; it is not the security boundary.
  // Manual approval after checking Selar remains the only path to an entitlement.
  const pool = getUnlockPool()
  const client = await pool.connect()
  try {
    await client.query('BEGIN')
    const result = await client.query(
      `INSERT INTO unlock_payments (reference, product_code, amount_cents, currency, status, submitted_at, expires_at, bot_id, buyer_email, buyer_name)
       VALUES ($1, 'bot-builder-unlock', 500, 'USD', 'pending', NOW(), NOW() + INTERVAL '45 minutes', $2::uuid, NULLIF($3, ''), NULLIF($4, ''))
       ON CONFLICT (reference) DO UPDATE SET submitted_at = COALESCE(unlock_payments.submitted_at, NOW()), bot_id = COALESCE(unlock_payments.bot_id, EXCLUDED.bot_id), buyer_email = COALESCE(unlock_payments.buyer_email, EXCLUDED.buyer_email), buyer_name = COALESCE(unlock_payments.buyer_name, EXCLUDED.buyer_name), updated_at = NOW()
       WHERE unlock_payments.status NOT IN ('verified', 'rejected', 'expired') AND (unlock_payments.expires_at IS NULL OR unlock_payments.expires_at > NOW())
       RETURNING id, status, submitted_at, notified_at`,
      [reference, botId, buyerEmail, buyerName],
    )
    if (!result.rows[0]) {
      await client.query('ROLLBACK')
      return NextResponse.json({ error: 'This payment is already finalized.' }, { status: 409 })
    }
    const payment = result.rows[0]
    if (!payment.notified_at) {
      await client.query('UPDATE unlock_payments SET notified_at = NOW(), updated_at = NOW() WHERE id = $1', [payment.id])
    }
    await client.query('COMMIT')
    return NextResponse.json({ status: 'pending', submitted: true, notified: !payment.notified_at })
  } catch {
    await client.query('ROLLBACK')
    return NextResponse.json({ error: 'Unable to submit payment' }, { status: 500 })
  } finally {
    client.release()
  }
}
