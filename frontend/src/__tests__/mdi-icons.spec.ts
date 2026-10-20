/// <reference types="node" />
/**
 * Every `mdi-*` icon name used in src must exist in the installed @mdi/font.
 * A missing name renders as an empty 24 px gap, so this fails loudly instead.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const sources = import.meta.glob<string>(
  ['/src/**/*.{vue,ts}', '!/src/**/__tests__/**', '!/src/**/*.spec.ts'],
  {
    query: '?raw',
    import: 'default',
    eager: true
  }
)

// Class names that are animation or utility helpers, not font glyphs.
const ALLOW_LIST = new Set(['mdi-spin'])

// Read with node fs: Vite's fs.allow rejects ?raw imports when node_modules is a symlink (git worktrees).
// Vitest runs from the frontend directory.
const mdiCss = readFileSync(
  resolve(process.cwd(), 'node_modules/@mdi/font/css/materialdesignicons.css'),
  'utf8'
)

const glyphs = new Set([...mdiCss.matchAll(/\.(mdi-[a-z0-9-]+)::before/g)].map(m => m[1]))

describe('mdi icon names', () => {
  it('finds glyphs in the installed @mdi/font', () => {
    expect(glyphs.has('mdi-alert')).toBe(true)
  })

  it('every mdi-* literal in src exists in @mdi/font', () => {
    const used = new Map<string, string[]>()
    for (const [file, text] of Object.entries(sources)) {
      for (const m of text.matchAll(/mdi-[a-z0-9-]+/g)) {
        const name = m[0]
        if (ALLOW_LIST.has(name)) continue
        used.set(name, [...(used.get(name) ?? []), file])
      }
    }
    const missing = [...used.keys()].filter(name => !glyphs.has(name))
    expect(missing.map(name => `${name} (${used.get(name)?.[0]})`)).toEqual([])
  })
})
