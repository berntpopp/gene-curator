/**
 * Every `mdi-*` icon name used in src must have a path in src/plugins/iconPaths.ts.
 * A missing name renders as an empty 24 px gap, so this fails loudly instead.
 */

import { describe, it, expect } from 'vitest'
import { mdiPaths } from '@/plugins/iconPaths'

const sources = import.meta.glob<string>(
  ['/src/**/*.{vue,ts}', '!/src/**/__tests__/**', '!/src/**/*.spec.ts', '!/src/plugins/icon*.ts'],
  {
    query: '?raw',
    import: 'default',
    eager: true
  }
)

// Class names that are animation or utility helpers, not glyphs; the icon plugin files are excluded above.
const ALLOW_LIST = new Set(['mdi-spin'])

describe('mdi icon names', () => {
  it('maps names to SVG paths', () => {
    expect(mdiPaths['mdi-alert']).toMatch(/^M/)
  })

  it('every mdi-* literal in src has an entry in the icon map', () => {
    const used = new Map<string, string[]>()
    for (const [file, text] of Object.entries(sources)) {
      for (const m of text.matchAll(/mdi-[a-z0-9-]+/g)) {
        const name = m[0]
        if (ALLOW_LIST.has(name)) continue
        used.set(name, [...(used.get(name) ?? []), file])
      }
    }
    const missing = [...used.keys()].filter(name => !(name in mdiPaths))
    expect(missing.map(name => `${name} (${used.get(name)?.[0]})`)).toEqual([])
  })
})
