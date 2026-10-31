/** MUI-02: a table placed in a tab section by dotted path still finds its row provenance. */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import TabContent from '../TabContent.vue'
import { ROW_PROVENANCE } from '../rowAuthorship'
import { createSchema, createTab } from './testHelpers'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))

describe('TabContent row authorship', () => {
  it('keys a nested table by its full path', () => {
    const w = mount(TabContent, {
      props: {
        tab: createTab([{ name: 'Genetic', fields: ['genetic.case_level'] }]),
        schema: createSchema({
          genetic: {
            type: 'object',
            properties: {
              case_level: { type: 'evidence_table', columns: { note: { type: 'string' } } }
            }
          }
        }),
        formData: { genetic: { case_level: [{ id: 'r1', note: 'x' }] } },
        readonly: true
      },
      global: {
        provide: {
          [ROW_PROVENANCE as symbol]: ref({
            'genetic.case_level#r1': { added_by: { name: 'Alice' }, added_at: '2026-10-02' }
          })
        }
      }
    })
    expect(w.text()).toContain('Added / changed')
    expect(w.find('.row-author').text()).toMatch(/^Added by Alice/)
  })
})
