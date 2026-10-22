import { describe, it, expect } from 'vitest'
import { conditionHolds } from '../conditions'
import cases from './conditionCases.json'

// The shared table (#433): backend/tests/unit/test_condition_cases.py runs the same cases
describe('conditionHolds', () => {
  it.each(cases.conditions)('$name', ({ condition, data, holds }) => {
    expect(conditionHolds(condition, data)).toBe(holds)
  })
})
