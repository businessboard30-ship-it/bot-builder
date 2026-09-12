import { NextRequest, NextResponse } from 'next/server'
import { getUnlockPool } from '@/lib/server-db'

export async function GET(request: NextRequest) {
  const reference = request.nextUrl.searchParams.get('reference')?.trim()
  if (!reference || !/^[A-Za-z0-9._:-]{6,160}$/.test(reference)) return NextResponse.json({ status: 'invalid' }, { status: 400 })

  const result = await getUnlockPool().query(
    `SELECT status, expires_at, submitted_at FROM unlock_payments WHERE reference = $1 LIMIT 1`,
    [reference],
  )
  const payment = result.rows[0]
  if (!payment) return NextResponse.json({ status: 'pending' })
  if (payment.status === 'pending' && payment.expires_at && new Date(payment.expires_at).getTime() <= Date.now()) {
    return NextResponse.json({ status: 'expired', expiresAt: payment.expires_at, submitted_at: payment.submitted_at })
  }
  return NextResponse.json({ status: payment.status, expiresAt: payment.expires_at, submitted_at: payment.submitted_at })
}
