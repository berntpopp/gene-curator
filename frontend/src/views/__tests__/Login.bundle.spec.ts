/**
 * #461: the seeded dev logins must be stripped from production builds, not just hidden.
 * Builds the real app (rolldown, ~1 s) and greps every emitted file.
 */
import { describe, it, expect, afterEach } from 'vitest'
import { build } from 'vite'
import { copyFileSync, mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const SEEDED = ['admin123', 'admin@genecurator.org', 'alice.smith@genecurator.org']
const original = { ...process.env }
let outDir = ''

// The repo's committed env files only: a developer's gitignored .env*.local must not decide the result.
function committedEnvDir(): string {
  const dir = mkdtempSync(join(tmpdir(), 'gc-env-'))
  for (const f of readdirSync('.').filter(n => /^\.env(\.production)?$/.test(n)))
    copyFileSync(f, join(dir, f))
  return dir
}

async function buildBundle(devLogin?: 'true'): Promise<string> {
  delete process.env.VITE_ENABLE_DEV_LOGIN // no inherited value; process env would win over .env files
  if (devLogin) process.env.VITE_ENABLE_DEV_LOGIN = devLogin
  process.env.NODE_ENV = 'production' // Vitest sets 'test', which would make import.meta.env.DEV true
  outDir = mkdtempSync(join(tmpdir(), 'gc-bundle-'))
  const envDir = committedEnvDir()
  await build({
    mode: 'production',
    envDir,
    logLevel: 'silent',
    build: { outDir, emptyOutDir: true }
  })
  rmSync(envDir, { recursive: true, force: true })
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
  it('contains no seeded credentials in a default production build', async () => {
    const bundle = await buildBundle()
    expect(SEEDED.filter(s => bundle.includes(s))).toEqual([])
  }, 60_000)

  it('keeps them when explicitly opted in (proves the search works)', async () => {
    const bundle = await buildBundle('true')
    expect(SEEDED.filter(s => bundle.includes(s))).toEqual(SEEDED)
  }, 60_000)
})
