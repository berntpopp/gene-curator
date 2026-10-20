import { afterEach, beforeAll, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import EvidenceItemDialog from '../EvidenceItemDialog.vue'

const existing = {
  evidence_type: 'genetic',
  evidence_category: 'case_level',
  description: 'Nonsense variant in proband',
  pmids: [],
  computed_score: 1.5,
  metadata: { variant_count: null, family_count: null, proband_count: null }
}

// The dialog teleports to <body>, so query the document rather than the wrapper.
function dialogButton(text: string): HTMLButtonElement {
  const button = Array.from(document.querySelectorAll('button')).find(b =>
    b.textContent?.includes(text)
  )
  if (!button) throw new Error(`no button "${text}"`)
  return button
}

describe('EvidenceItemDialog', () => {
  let wrapper: VueWrapper | undefined

  // Vuetify's overlay reads visualViewport, which happy-dom does not provide.
  beforeAll(() => {
    if (!('visualViewport' in globalThis)) {
      Object.defineProperty(globalThis, 'visualViewport', {
        value: {
          width: 1024,
          height: 768,
          scale: 1,
          offsetLeft: 0,
          offsetTop: 0,
          pageLeft: 0,
          pageTop: 0,
          addEventListener() {},
          removeEventListener() {}
        }
      })
    }
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
  })

  function mountDialog(props: Record<string, unknown>) {
    wrapper = mount(EvidenceItemDialog, { props: props as never, attachTo: document.body })
    return wrapper
  }

  it('titles the dialog for adding genetic evidence and shows the genetic maximum', () => {
    mountDialog({ modelValue: true, evidenceType: 'genetic' })
    expect(document.body.textContent).toContain('Add Genetic Evidence')
    expect(document.body.textContent).toContain('Maximum 12 points for Genetic evidence')
  })

  it('uses the experimental maximum of 6 points for experimental evidence', () => {
    mountDialog({ modelValue: true, evidenceType: 'experimental' })
    expect(document.body.textContent).toContain('Maximum 6 points for Experimental evidence')
  })

  it('switches to edit mode when an existing evidence item is provided', () => {
    mountDialog({ modelValue: true, evidenceType: 'genetic', evidence: existing })
    expect(document.body.textContent).toContain('Edit Genetic Evidence')
    expect(dialogButton('Update Evidence')).toBeDefined()
  })

  it('emits update:modelValue false when cancelled', () => {
    mountDialog({ modelValue: true, evidenceType: 'genetic' })
    dialogButton('Cancel').click()
    expect(wrapper?.emitted('update:modelValue')?.[0]).toEqual([false])
  })

  it('saves a valid item with empty metadata cleaned to null', async () => {
    mountDialog({ modelValue: true, evidenceType: 'genetic', evidence: existing })
    dialogButton('Update Evidence').click()
    await flushPromises()

    const saved = wrapper?.emitted('save')?.[0]?.[0] as {
      metadata: unknown
      computed_score: number
    }
    expect(saved.metadata).toBeNull()
    expect(saved.computed_score).toBe(1.5)
  })

  it('keeps only the metadata counts that were filled in', async () => {
    mountDialog({
      modelValue: true,
      evidenceType: 'genetic',
      evidence: {
        ...existing,
        metadata: { variant_count: 3, family_count: null, proband_count: '' }
      }
    })
    dialogButton('Update Evidence').click()
    await flushPromises()

    const saved = wrapper?.emitted('save')?.[0]?.[0] as { metadata: unknown }
    expect(saved.metadata).toEqual({ variant_count: 3 })
  })

  it('does not save when the description is missing', async () => {
    mountDialog({
      modelValue: true,
      evidenceType: 'genetic',
      evidence: { ...existing, description: '' }
    })
    dialogButton('Update Evidence').click()
    await flushPromises()
    expect(wrapper?.emitted('save')).toBeUndefined()
  })
})
