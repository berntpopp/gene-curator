/** #593: source cells (VA-Spec Document) and row authorship on evidence rows. */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EvidenceTableField from '../EvidenceTableField.vue'
import SourceCell from '../SourceCell.vue'
import { normalizeField } from '../normalizeDefinition'
import { FIELD_PATH, ROW_PROVENANCE, rowAuthorship, rowTools, stampOf } from '../rowAuthorship'
import { ref } from 'vue'
import { detectSource, sourceError, sourceHref, sourceList, sourceDetail } from '../sourceModel'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))

const CLINVAR = {
  kind: 'clinvar',
  id: 'VCV000012345',
  tool: 'genefoundry:clinvar_get_variant',
  retrieved_at: '2026-10-02'
}
const AGENT = {
  model: 'claude-opus-5-5',
  agent: 'Claude Code',
  tools_used: ['genefoundry:clinvar']
}
const ROW = { id: 'r1', label: 'P1', sources: [CLINVAR, { kind: 'pmid', id: '123' }] }
const STAMP = {
  added_by: { name: 'Alice', agent: AGENT },
  added_at: '2026-10-02T09:00:00Z',
  changed_by: { name: 'Bob' },
  changed_at: '2026-10-03T09:00:00Z'
}
const table = normalizeField({
  type: 'evidence_table',
  columns: { label: { type: 'text' }, sources: { type: 'source', label: 'Sources' } }
})

describe('sourceModel', () => {
  it('checks ids per kind like the server', () => {
    expect(sourceError('clinvar', 'VCV000012345')).toBe('')
    expect(sourceError('clinvar', 'VCV12')).toBe('Not a valid ClinVar id')
    expect(sourceError('doi', '10.1038/abc')).toBe('')
    expect(sourceError('clingen_allele', 'CA1')).toBe('')
    expect(sourceError('clingen_validity', 'CGGV:1')).toBe('Not a valid ClinGen validity id')
    expect(sourceError('pmid', ' ')).toBe('Enter an id')
    expect(sourceError('book', 'x')).toBe('Pick a kind')
  })

  it('links only safe URLs and lists one or many sources', () => {
    expect(sourceHref({ kind: 'pmid', id: '123' })).toBe('https://pubmed.ncbi.nlm.nih.gov/123/')
    expect(sourceHref({ kind: 'doi', id: '10.1/x' })).toBe('https://doi.org/10.1/x')
    expect(sourceHref({ kind: 'url', id: 'javascript:alert(1)' })).toBeUndefined()
    expect(sourceHref({ kind: 'database', id: 'LOVD 1' })).toBeUndefined()
    expect(sourceList(CLINVAR)).toEqual([CLINVAR])
    expect(sourceList(null)).toEqual([])
    expect(sourceDetail(CLINVAR)).toBe('via genefoundry:clinvar_get_variant · retrieved 2026-10-02')
  })
})

describe('SourceCell', () => {
  it('reads the kind from the id: no picker (UX)', () => {
    expect(detectSource('20414234')).toEqual({ kind: 'pmid', id: '20414234' })
    expect(detectSource(' PMID: 20414234 ')).toEqual({ kind: 'pmid', id: '20414234' })
    expect(detectSource('VCV000012345')).toEqual({ kind: 'clinvar', id: 'VCV000012345' })
    expect(detectSource('doi:10.1038/abc')).toEqual({ kind: 'doi', id: '10.1038/abc' })
    expect(detectSource('CA123')).toEqual({ kind: 'clingen_allele', id: 'CA123' })
    expect(detectSource('CGGV:assertion_x')).toEqual({
      kind: 'clingen_validity',
      id: 'CGGV:assertion_x'
    })
    expect(detectSource('LOVD 1')).toEqual({ kind: 'database', id: 'LOVD 1' })
    expect(detectSource('PMID 123')).toEqual({ kind: 'pmid', id: '123' })
    expect(detectSource('pmid123')).toEqual({ kind: 'pmid', id: '123' })
    expect(detectSource('DOI 10.1/x')).toEqual({ kind: 'doi', id: '10.1/x' })
    expect(detectSource('vcv000012345')).toEqual({ kind: 'clinvar', id: 'VCV000012345' })
    expect(detectSource('ca123')).toEqual({ kind: 'clingen_allele', id: 'CA123' })
  })

  it('adds sources as chips by Enter or Add and removes them', async () => {
    const wrapper = mount(SourceCell, { props: { modelValue: [CLINVAR], ariaLabel: 'Sources' } })
    expect(wrapper.find('select').exists()).toBe(false)
    const input = wrapper.find('input')
    await input.trigger('keydown.enter')
    expect(wrapper.emitted('update:model-value')).toBeUndefined()
    await input.setValue('PMID:42')
    expect(wrapper.find('.source-cell__kind').text()).toBe('PMID')
    await input.trigger('keydown.enter')
    expect(wrapper.emitted('update:model-value')![0]![0]).toEqual([
      CLINVAR,
      { kind: 'pmid', id: '42' }
    ])
    expect((input.element as HTMLInputElement).value).toBe('')
    await wrapper.find('[aria-label="Remove ClinVar VCV000012345"]').trigger('click')
    expect(wrapper.emitted('update:model-value')![1]![0]).toEqual([])
  })
})

describe('SourceCell removal', () => {
  it('removing the first of two keeps the second visible (review #608)', async () => {
    const PM = { kind: 'pmid', id: '42' }
    const wrapper = mount(SourceCell, { props: { modelValue: [CLINVAR, PM] } })
    await wrapper.find('[aria-label="Remove ClinVar VCV000012345"]').trigger('click')
    await wrapper.setProps({ modelValue: wrapper.emitted('update:model-value')![0]![0] })
    expect(wrapper.text()).toContain('PMID 42')
    expect(wrapper.findAll('.v-chip')).toHaveLength(1)
  })
})

describe('row authorship', () => {
  it('names the person, the agent and the change', () => {
    expect(stampOf({ 'genetic.probands#r1': STAMP }, 'genetic.probands', ROW, 0)).toBe(STAMP)
    expect(stampOf({ 'rows[2]': STAMP }, 'rows', { v: 1 }, 2)).toBe(STAMP)
    expect(stampOf(null, 'rows', ROW, 0)).toBeUndefined()
    expect(rowAuthorship(STAMP)).toMatch(
      /^Added by Alice via Claude Code \(claude-opus-5-5\), .+; Changed by Bob, .+$/
    )
    expect(rowTools(STAMP)).toEqual(['genefoundry:clinvar'])
    expect(rowAuthorship(undefined)).toBe('')
  })

  it('shows sources as links and the authorship column in a readonly table', async () => {
    const wrapper = mount(EvidenceTableField, {
      props: {
        fieldSchema: table,
        fieldName: 'probands',
        label: 'Probands',
        modelValue: [ROW],
        readonly: true
      },
      global: {
        provide: {
          [ROW_PROVENANCE as symbol]: ref({ 'genetic.probands#r1': STAMP }),
          [FIELD_PATH as symbol]: 'genetic.'
        }
      }
    })
    await flushPromises()
    expect(wrapper.findAll('a').map(a => a.attributes('href'))).toEqual([
      'https://www.ncbi.nlm.nih.gov/clinvar/?term=VCV000012345',
      'https://pubmed.ncbi.nlm.nih.gov/123/'
    ])
    expect(wrapper.text()).toContain('Added / changed')
    expect(wrapper.find('.row-author').text()).toContain('via Claude Code')
    expect(wrapper.findAll('input')).toHaveLength(0)
  })
})
