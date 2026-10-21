import { describe, it, expect } from 'vitest'
import { ESLint } from 'eslint'

// One instance: building the config per case is slow and timed out under load.
const eslint = new ESLint()

describe('native dialog ban', () => {
  it.each(['window.confirm("x")', 'globalThis.alert("x")', 'window.prompt("x")', 'confirm("x")'])(
    'rejects %s',
    async code => {
      const [result] = await eslint.lintText(code, { filePath: 'src/probe.ts' })
      const rules = result?.messages.map(m => m.ruleId) ?? []
      expect(
        rules.some(r => r === 'no-restricted-properties' || r === 'no-restricted-globals')
      ).toBe(true)
    },
    30_000
  )
})
