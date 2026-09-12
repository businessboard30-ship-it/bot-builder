import { Pool } from 'pg'

const globalForDb = globalThis as unknown as { unlockPool?: Pool }

export function getUnlockPool() {
  if (!process.env.DATABASE_URL) throw new Error('DATABASE_URL is not configured')
  globalForDb.unlockPool ??= new Pool({ connectionString: process.env.DATABASE_URL, max: 3 })
  return globalForDb.unlockPool
}
