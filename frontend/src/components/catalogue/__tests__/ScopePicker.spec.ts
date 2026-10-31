import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopePicker from '../ScopePicker.vue'

const scopes = Array.from({ length: 30 }, (_, i) => ({
  id: `s${i}`,
  name: `scope-${i}`,
  display_name: i === 3 ? 'Cilia' : `Scope ${i}`
}))

function mountPicker(props: Record<string, unknown> = {}) {
  return mount(ScopePicker, {
    props: { scopes, modelValue: ['s0', 's1', 's2'], mine: ['s5', 's6'], ...props },
    attachTo: document.body
  })
}
const open = async (w: ReturnType<typeof mountPicker>) => {
  await w.find('[data-testid="scope-picker"]').trigger('click')
  await new Promise(r => setTimeout(r, 50))
}
const body = () => document.body

describe('ScopePicker', () => {
  it('labels the button with shown and total counts', () => {
    const w = mountPicker()
    expect(w.find('[data-testid="scope-picker"]').text()).toBe('Scopes shown: 3 of 30')
    w.unmount()
  })

  it('toggles a scope and emits the new selection in list order', async () => {
    const w = mountPicker()
    await open(w)
    ;(body().querySelector('[data-testid="scope-s9"] input') as HTMLInputElement).click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s0', 's1', 's2', 's9']])
    ;(body().querySelector('[data-testid="scope-s0"] input') as HTMLInputElement).click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s1', 's2']])
    w.unmount()
  })

  it('filters the list by the search text', async () => {
    const w = mountPicker()
    await open(w)
    const input = body().querySelector('[data-testid="scope-search"] input') as HTMLInputElement
    input.value = 'cilia'
    input.dispatchEvent(new Event('input'))
    await new Promise(r => setTimeout(r, 20))
    expect(
      body().querySelectorAll('[data-testid^="scope-s"]:not([data-testid="scope-search"])').length
    ).toBe(1)
    w.unmount()
  })

  it('applies presets, hiding My scopes when there are none', async () => {
    const w = mountPicker()
    await open(w)
    ;(body().querySelector('[data-testid="preset-mine"]') as HTMLElement).click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s5', 's6']])
    ;(body().querySelector('[data-testid="preset-all"]') as HTMLElement).click()
    expect((w.emitted('update:modelValue')?.at(-1)![0] as string[]).length).toBe(30)
    w.unmount()
    const bare = mountPicker({ mine: [] })
    await open(bare)
    expect(body().querySelector('[data-testid="preset-mine"]')).toBeNull()
    bare.unmount()
  })

  it('offers a With results preset only when some scopes have results (#276)', async () => {
    const w = mountPicker({ withResults: ['s7', 's8'] })
    await open(w)
    ;(body().querySelector('[data-testid="preset-results"]') as HTMLElement).click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s7', 's8']])
    w.unmount()
    const bare = mountPicker()
    await open(bare)
    expect(body().querySelector('[data-testid="preset-results"]')).toBeNull()
    bare.unmount()
  })

  it('keeps the column order when ticking: a new scope joins at the end (#276)', async () => {
    const w = mountPicker({ modelValue: ['s2', 's0'] })
    await open(w)
    ;(body().querySelector('[data-testid="scope-s1"] input') as HTMLInputElement).click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s2', 's0', 's1']])
    w.unmount()
  })

  it('reorders columns with the keyboard-reachable arrow buttons (#276)', async () => {
    const w = mountPicker()
    await open(w)
    const btn = (label: string) =>
      body().querySelector(`[aria-label="${label}"]`) as HTMLButtonElement
    expect(btn('Move Scope 0 left').disabled).toBe(true)
    expect(btn('Move Scope 2 right').disabled).toBe(true)
    btn('Move Scope 0 right').click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s1', 's0', 's2']])
    btn('Move Scope 2 left').click()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s0', 's2', 's1']])
    w.unmount()
  })

  it('reorders columns by drag and drop (#276)', async () => {
    const w = mountPicker()
    await open(w)
    const item = (id: string) => body().querySelector(`[data-testid="order-${id}"]`)!
    expect(item('s0').getAttribute('draggable')).toBe('true')
    item('s2').dispatchEvent(new Event('dragstart', { bubbles: true }))
    item('s0').dispatchEvent(new Event('drop', { bubbles: true, cancelable: true }))
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual([['s2', 's0', 's1']])
    // a drop with no drag in progress, or onto itself, changes nothing
    item('s1').dispatchEvent(new Event('drop', { bubbles: true, cancelable: true }))
    item('s1').dispatchEvent(new Event('dragstart', { bubbles: true }))
    item('s1').dispatchEvent(new Event('drop', { bubbles: true, cancelable: true }))
    expect(w.emitted('update:modelValue')).toHaveLength(1)
    w.unmount()
  })

  it('offers a Disagreements preset that asks for disagreeing rows (#276)', async () => {
    const w = mountPicker()
    await open(w)
    ;(body().querySelector('[data-testid="preset-disagreements"]') as HTMLElement).click()
    expect(w.emitted('disagreements')).toHaveLength(1)
    expect(w.emitted('update:modelValue')).toBeUndefined()
    w.unmount()
  })

  it('keeps the last shown scope checked and disabled', async () => {
    const w = mountPicker({ modelValue: ['s4'] })
    await open(w)
    const box = body().querySelector('[data-testid="scope-s4"] input') as HTMLInputElement
    expect(box.disabled).toBe(true)
    w.unmount()
  })
})
