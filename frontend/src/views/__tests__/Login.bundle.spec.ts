/**
 * #461: the seeded dev logins must be stripped from production builds, not just hidden.
 * Builds the real app (rolldown, ~1 s) and greps every emitted file.
 */
import { describe, it, expect, afterEach } from 'vitest'
import { build } from 'vite'
import { mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const SEEDED = ['admin123', 'admin@genecurator.org', 'alice.smith@genecurator.org']
const original = { ...process.env }
let outDir = ''

async function buildBundle(devLogin: 'true' | 'false'): Promise<string> {
  process.env.VITE_ENABLE_DEV_LOGIN = devLogin // process env wins over .env files
  process.env.NODE_ENV = 'production' // Vitest sets 'test', which would make import.meta.env.DEV true
  outDir = mkdtempSync(join(tmpdir(), 'gc-bundle-'))
  await build({ mode: 'production', logLevel: 'silent', build: { outDir, emptyOutDir: true } })
  return readdirSync(outDir, { recursive: true, withFileTypes: true })
    .filter(f => f.isFile())
    .map(f => readFileSync(join(f.parentPath, f.name), 'utf8'))
    .join('\n')
}

afterEach(() => {
  process.env = { ...original }
  rmSync(outDir, { recursive: true, force: true })
})

describe('Login production bundle', () => {
  it('contains no seeded credentials when dev login is off', async () => {
    const bundle = await buildBundle('false')
    expect(SEEDED.filter(s => bundle.includes(s))).toEqual([])
  }, 60_000)

  it('keeps them when VITE_ENABLE_DEV_LOGIN=true (dev Docker UI)', async () => {
    const bundle = await buildBundle('true')
    expect(SEEDED.filter(s => bundle.includes(s))).toEqual(SEEDED)
  }, 60_000)
})
