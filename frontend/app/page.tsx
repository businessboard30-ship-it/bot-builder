export default function Home() {
  return (
    <main className="min-h-screen bg-background px-6 py-16 text-foreground">
      <div className="mx-auto max-w-2xl space-y-6">
        <p className="font-mono text-sm uppercase tracking-[0.24em] text-muted-foreground">Bot Builder</p>
        <h1 className="text-4xl font-semibold tracking-tight">Build your Discord bot inside Discord.</h1>
        <p className="max-w-xl text-lg leading-8 text-muted-foreground">
          This web surface does not contain the build flow. Invite the main bot, run <code className="rounded bg-muted px-2 py-1 font-mono text-sm">/build</code>, and complete setup with Discord buttons, select menus, and modals.
        </p>
      </div>
    </main>
  )
}
