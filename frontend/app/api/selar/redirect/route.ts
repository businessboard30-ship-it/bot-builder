import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const reference = request.nextUrl.searchParams.get('reference')?.trim()
  const botId = request.nextUrl.searchParams.get('bot_id')?.trim()
  if (!reference || !/^[A-Za-z0-9._:-]{6,160}$/.test(reference) || !botId || !/^[0-9a-f-]{36}$/i.test(botId)) {
    return NextResponse.redirect(new URL('/unlock?state=invalid', request.url))
  }

  return NextResponse.redirect(new URL(`/unlock?reference=${encodeURIComponent(reference)}&bot_id=${encodeURIComponent(botId)}&state=pending`, request.url))
}
