import { describe, expect, it } from 'vitest'

// Vuetify 4 removed the MD2 typography classes; they render unstyled.
const LEGACY = /(?<![\w-])text-(h[1-6]|subtitle-[12]|body-[12]|caption|button|overline)(?![\w-])/

const sources = import.meta.glob<string>('/src/**/*.{vue,ts,scss,css,snap}', {
  query: '?raw',
  import: 'default',
  eager: true
})

describe('legacy Vuetify 3 typography classes', () => {
  it('are absent from src', () => {
    const hits = Object.entries(sources)
      .filter(([file, text]) => !file.endsWith('legacy-typography.spec.ts') && LEGACY.test(text))
      .map(([file]) => file)
    expect(hits).toEqual([])
  })
})
