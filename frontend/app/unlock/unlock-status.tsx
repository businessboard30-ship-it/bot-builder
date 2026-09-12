'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { useEffect, useState } from 'react'

export function UnlockStatus() {
  const params = useSearchParams()
  const reference = params.get('reference') ?? ''
  const botId = params.get('bot_id') ?? ''
  const invalid = params.get('state') === 'invalid'
  const [status, setStatus] = useState(invalid ? 'invalid' : 'pending')
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [notified, setNotified] = useState(false)
  const [buyerEmail, setBuyerEmail] = useState('')
  const [buyerName, setBuyerName] = useState('')

  useEffect(() => {
    if (!reference || invalid) return
    let cancelled = false
    const check = async () => {
      try {
        const response = await fetch(`/api/unlock/status?reference=${encodeURIComponent(reference)}`, { cache: 'no-store' })
        const body = await response.json()
        if (!cancelled) {
          setStatus(body.status ?? 'pending')
          setSubmitted(Boolean(body.submitted_at))
        }
      } catch {
        if (!cancelled) setError('Status is temporarily unavailable. Please try again shortly.')
      }
    }
    void check()
    const timer = window.setInterval(check, 5000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [reference, invalid])

  async function submitPaid() {
    setSubmitting(true)
    setError('')
    try {
      const response = await fetch('/api/selar/submit', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ reference, bot_id: botId, buyer_email: buyerEmail, buyer_name: buyerName }) })
      const body = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(body.error ?? 'Unable to submit payment')
      setSubmitted(true)
      setNotified(Boolean(body.notified))
      setStatus('pending')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to submit payment')
    } finally { setSubmitting(false) }
  }

  const finalized = status === 'verified' || status === 'rejected' || status === 'invalid'
  const label = status === 'verified' ? 'Unlocked' : status === 'rejected' || status === 'invalid' ? 'Not verified' : 'Submitted — awaiting confirmation'

  return (
    <main className="min-h-screen bg-background px-6 py-16 text-foreground">
      <div className="mx-auto max-w-xl space-y-8">
        <div className="space-y-3">
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted-foreground">Bot Builder / Unlock</p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance">{status === 'verified' ? 'Your unlock is active.' : 'Confirm your payment'}</h1>
          <p className="text-lg leading-8 text-muted-foreground">Bot Builder unlock · $5.00 USD</p>
        </div>
        <section className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p className="text-sm font-medium">Order details</p>
          <p className="mt-2 text-2xl font-semibold">Bot Builder unlock</p>
          <p className="mt-1 text-muted-foreground">$5.00 USD</p>
          {reference && <p className="mt-4 break-all font-mono text-xs text-muted-foreground">Reference: {reference}</p>}
          {!finalized && !submitted && <div className="mt-6 space-y-3"><label className="block text-sm"><span className="mb-1 block text-muted-foreground">Name (optional)</span><input value={buyerName} onChange={(event) => setBuyerName(event.target.value)} className="w-full rounded-lg border border-border bg-background px-3 py-2" maxLength={120} /></label><label className="block text-sm"><span className="mb-1 block text-muted-foreground">Email (optional)</span><input type="email" value={buyerEmail} onChange={(event) => setBuyerEmail(event.target.value)} className="w-full rounded-lg border border-border bg-background px-3 py-2" maxLength={320} /></label><button type="button" onClick={submitPaid} disabled={!reference || !botId || submitting} className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">{submitting ? 'Submitting…' : "I've Paid"}</button></div>}
          <p className="mt-6 text-sm leading-6 text-muted-foreground">{invalid ? 'The payment reference is missing or invalid.' : finalized ? label : submitted ? `Submitted — awaiting confirmation. ${notified ? 'The administrator was notified.' : 'Your submission was recorded.'} Approval is completed manually after checking the Selar sales dashboard.` : 'Tap “I\'ve Paid” after completing checkout. This notifies the administrator but does not unlock access.'}</p>
          {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
        </section>
        <Link className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground" href="/">Return to builder</Link>
      </div>
    </main>
  )
}
