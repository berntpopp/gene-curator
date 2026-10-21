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

  it('keeps the last shown scope checked and disabled', async () => {
    const w = mountPicker({ modelValue: ['s4'] })
    await open(w)
    const box = body().querySelector('[data-testid="scope-s4"] input') as HTMLInputElement
    expect(box.disabled).toBe(true)
    w.unmount()
  })
})
