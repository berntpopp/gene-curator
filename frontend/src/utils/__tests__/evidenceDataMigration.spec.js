import { describe, it, expect } from 'vitest'
import { migrateLegacyFormat, isLegacyFormat } from '../evidenceDataMigration'

describe('evidenceDataMigration', () => {
  describe('isLegacyFormat', () => {
    it('returns falsy for null/undefined', () => {
      expect(isLegacyFormat(null)).toBeFalsy()
      expect(isLegacyFormat(undefined)).toBeFalsy()
    })

    it('returns false for empty object', () => {
      expect(isLegacyFormat({})).toBe(false)
    })

    it('returns false for already migrated data', () => {
      expect(isLegacyFormat({ _version: '2.0', disease_name: 'Test' })).toBe(false)
    })

    it('returns true for data with evidence_items', () => {
      expect(isLegacyFormat({ evidence_items: [] })).toBe(true)
    })

    it('returns true for data with disease_entity', () => {
      expect(isLegacyFormat({ disease_entity: { name: 'Test' } })).toBe(true)
    })
  })

  describe('migrateLegacyFormat', () => {
    it('returns unchanged if already migrated', () => {
      const data = { _version: '2.0', disease_name: 'Test Disease' }
      const result = migrateLegacyFormat(data)
      expect(result).toEqual(data)
    })

    it('returns unchanged with version for non-legacy format', () => {
      const data = { disease_name: 'Test', mode_of_inheritance: 'AD' }
      const result = migrateLegacyFormat(data)
      expect(result._version).toBe('2.0')
      expect(result.disease_name).toBe('Test')
    })

    it('migrates disease_entity to flat fields', () => {
      const legacy = {
        disease_entity: {
          name: 'SCN1A-related seizure disorder',
          mondo_id: 'MONDO:0000001',
          inheritance: 'Autosomal Dominant'
        }
      }
      const result = migrateLegacyFormat(legacy)
      expect(result._version).toBe('2.0')
      expect(result.disease_name).toBe('SCN1A-related seizure disorder')
      expect(result.mondo_id).toBe('MONDO:0000001')
      expect(result.mode_of_inheritance).toBe('Autosomal Dominant')
    })

    it('preserves genetic_evidence structure', () => {
      const legacy = {
        genetic_evidence: {
          case_level_score: 5,
          segregation_score: 2
        }
      }
      const result = migrateLegacyFormat(legacy)
      expect(result.genetic_evidence).toEqual(legacy.genetic_evidence)
    })

    it('preserves experimental_evidence structure', () => {
      const legacy = {
        experimental_evidence: {
          functional_score: 2,
          model_system_score: 1
        }
      }
      const result = migrateLegacyFormat(legacy)
      expect(result.experimental_evidence).toEqual(legacy.experimental_evidence)
    })

    it('handles null/undefined gracefully', () => {
      expect(migrateLegacyFormat(null)).toBe(null)
      expect(migrateLegacyFormat(undefined)).toBe(undefined)
    })

    it('handles empty object', () => {
      const result = migrateLegacyFormat({})
      expect(result).toEqual({})
    })

    it('preserves top-level fields not in disease_entity', () => {
      const legacy = {
        disease_entity: { name: 'Test' },
        curator_notes: 'Some notes',
        pmids: ['12345', '67890']
      }
      const result = migrateLegacyFormat(legacy)
      expect(result.curator_notes).toBe('Some notes')
      expect(result.pmids).toEqual(['12345', '67890'])
    })

    it('top-level fields override disease_entity due to spread order', () => {
      const legacy = {
        disease_name: 'Top level name',
        disease_entity: { name: 'Entity name' }
      }
      const result = migrateLegacyFormat(legacy)
      // Spread happens after disease_entity extraction, so top-level wins
      expect(result.disease_name).toBe('Top level name')
    })

    it('falls back to top-level disease_name when disease_entity.name is empty', () => {
      const legacy = {
        disease_name: 'Fallback name',
        disease_entity: { name: '' }
      }
      const result = migrateLegacyFormat(legacy)
      expect(result.disease_name).toBe('Fallback name')
    })
  })
})
