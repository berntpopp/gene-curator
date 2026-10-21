import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

// Vuetify 4 removed the MD2 typography classes; they render unstyled.
const LEGACY = /(?<![\w-])text-(h[1-6]|subtitle-[12]|body-[12]|caption|button|overline)(?![\w-])/

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap(name => {
    const p = join(dir, name)
    return statSync(p).isDirectory() ? walk(p) : [p]
  })
}

describe('legacy Vuetify 3 typography classes', () => {
  it('are absent from src', () => {
    const self = __filename
    const hits = walk(join(__dirname, '..'))
      .filter(f => /\.(vue|ts|scss|css|snap)$/.test(f) && f !== self)
      .filter(f => LEGACY.test(readFileSync(f, 'utf8')))
    expect(hits).toEqual([])
  })
})
