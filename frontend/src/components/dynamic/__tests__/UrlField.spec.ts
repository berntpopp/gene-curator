/** #538: `url` fields and evidence-table columns render safe clickable links. */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DynamicField from '../DynamicField.vue'
import EvidenceTableField from '../EvidenceTableField.vue'
import { safeHref, urlRule } from '../componentRegistry'
import { normalizeField } from '../normalizeDefinition'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))

const URL = 'https://www.erknet.org/subregistries/adtkd-registry'
const BAD = [
  'javascript:alert(1)',
  'data:text/html,x',
  'ftp://x.org',
  'adtkd.de',
  'https://exa mple.com',
  '',
  null,
  5
]

const links = (w: ReturnType<typeof mount>) =>
  w.findAll('a').map(a => [a.attributes('href'), a.attributes('target'), a.attributes('rel')])
const safe = [[URL, '_blank', 'noopener noreferrer']]

describe('url fields', () => {
  it('link only http(s) URLs with a host', () => {
    expect(safeHref(` ${URL} `)).toBe(URL)
    expect(safeHref('https://www.medrxiv.org/content/10.64898/2026.05.27.26352937v1')).toBeTruthy()
    for (const v of BAD) expect(safeHref(v)).toBeUndefined()
    expect(urlRule('')).toBe(true)
    expect(urlRule(URL)).toBe(true)
    expect(urlRule('javascript:alert(1)')).toBe('Enter an http(s) URL')
  })

  it.each([false, true])('render a safe link in the form field (readonly=%s)', async readonly => {
    const fieldSchema = normalizeField({ type: 'url', label: 'Registry' })
    const props = { fieldName: 'registry', fieldSchema, modelValue: URL, readonly }
    const w = mount(DynamicField, { props })
    expect(w.text()).not.toContain('Unknown Type')
    expect(w.find('input').exists()).toBe(!readonly)
    expect(links(w)).toEqual(safe)
    await w.setProps({ modelValue: 'javascript:alert(1)' })
    expect(w.findAll('a')).toHaveLength(0)
  })

  it('emits typed URLs from the edit field', async () => {
    const fieldSchema = normalizeField({ type: 'url' })
    const w = mount(DynamicField, { props: { fieldName: 'u', fieldSchema, modelValue: '' } })
    await w.find('input').setValue(URL)
    expect(w.emitted('update:model-value')?.at(-1)).toEqual([URL])
  })

  it.each([false, true])('link url cells of an evidence table (readonly=%s)', async readonly => {
    const fieldSchema = normalizeField({
      type: 'evidence_table',
      columns: { name: { type: 'text' }, link: { type: 'url', label: 'Link' } }
    })
    const modelValue = [
      { id: 'a', name: 'ERKNet', link: URL },
      { id: 'b', name: 'bad', link: 'data:text/html,x' }
    ]
    const w = mount(EvidenceTableField, {
      props: { fieldSchema, label: 'Resources', modelValue, readonly }
    })
    await flushPromises()
    expect(links(w)).toEqual(safe)
    if (readonly) expect(w.text()).toContain('data:text/html,x') // shown, never linked
  })
})
