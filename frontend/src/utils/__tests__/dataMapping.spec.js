import { describe, it, expect } from 'vitest'
import { applyDataMapping } from '../dataMapping'

describe('applyDataMapping', () => {
  it('maps flat source fields to nested target paths', () => {
    const precurationData = {
      mondo_id: 'MONDO:0000001',
      disease_name: 'Test Disease'
    }
    const dataMapping = {
      precuration_to_curation: {
        mondo_id: 'entity_definition.mondo_id',
        disease_name: 'entity_definition.disease_name'
      }
    }

    const result = applyDataMapping(precurationData, dataMapping)

    expect(result).toEqual({
      entity_definition: {
        mondo_id: 'MONDO:0000001',
        disease_name: 'Test Disease'
      }
    })
  })

  it('skips missing source fields', () => {
    const precurationData = {
      mondo_id: 'MONDO:0000001'
    }
    const dataMapping = {
      precuration_to_curation: {
        mondo_id: 'mondo_id',
        disease_name: 'disease_name',
        missing_field: 'target'
      }
    }

    const result = applyDataMapping(precurationData, dataMapping)

    expect(result).toEqual({
      mondo_id: 'MONDO:0000001'
    })
    expect(result).not.toHaveProperty('disease_name')
    expect(result).not.toHaveProperty('target')
  })

  it('creates deeply nested target objects', () => {
    const precurationData = {
      moi_code: 'AD'
    }
    const dataMapping = {
      precuration_to_curation: {
        moi_code: 'genetic_evidence.inheritance.mode'
      }
    }

    const result = applyDataMapping(precurationData, dataMapping)

    expect(result).toEqual({
      genetic_evidence: {
        inheritance: {
          mode: 'AD'
        }
      }
    })
  })

  it('returns empty object for null/undefined precurationData', () => {
    const dataMapping = {
      precuration_to_curation: { mondo_id: 'mondo_id' }
    }

    expect(applyDataMapping(null, dataMapping)).toEqual({})
    expect(applyDataMapping(undefined, dataMapping)).toEqual({})
  })

  it('returns empty object for null/undefined dataMapping', () => {
    const precurationData = { mondo_id: 'MONDO:0000001' }

    expect(applyDataMapping(precurationData, null)).toEqual({})
    expect(applyDataMapping(precurationData, undefined)).toEqual({})
  })

  it('returns empty object when precuration_to_curation key is missing', () => {
    const precurationData = { mondo_id: 'MONDO:0000001' }
    const dataMapping = { some_other_key: { mondo_id: 'mondo_id' } }

    const result = applyDataMapping(precurationData, dataMapping)

    expect(result).toEqual({})
  })

  it('handles flat-to-flat mapping', () => {
    const precurationData = {
      mondo_id: 'MONDO:0000001',
      mode_of_inheritance: 'AR'
    }
    const dataMapping = {
      precuration_to_curation: {
        mondo_id: 'mondo_id',
        mode_of_inheritance: 'moi'
      }
    }

    const result = applyDataMapping(precurationData, dataMapping)

    expect(result).toEqual({
      mondo_id: 'MONDO:0000001',
      moi: 'AR'
    })
  })
})
