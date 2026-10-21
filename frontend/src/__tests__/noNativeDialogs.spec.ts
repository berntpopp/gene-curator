import { describe, it, expect } from 'vitest'
import { ESLint } from 'eslint'

describe('native dialog ban', () => {
  it.each(['window.confirm("x")', 'globalThis.alert("x")', 'window.prompt("x")', 'confirm("x")'])(
    'rejects %s',
    async code => {
      const eslint = new ESLint()
      const [result] = await eslint.lintText(code, { filePath: 'src/probe.ts' })
      const rules = result?.messages.map(m => m.ruleId) ?? []
      expect(
        rules.some(r => r === 'no-restricted-properties' || r === 'no-restricted-globals')
      ).toBe(true)
    }
  )
})
