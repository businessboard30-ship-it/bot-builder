import { Suspense } from 'react'
import { UnlockStatus } from './unlock-status'

export default function UnlockPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-background px-6 py-16 text-foreground"><div className="mx-auto max-w-xl"><p className="text-sm text-muted-foreground">Checking unlock status...</p></div></main>}>
      <UnlockStatus />
    </Suspense>
  )
}
