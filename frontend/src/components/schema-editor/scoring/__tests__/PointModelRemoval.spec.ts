/** MUI-08: removing a section, category or evidence type asks first. */
import { describe, it, expect, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PointModelSections from '../PointModelSections.vue'
import PointModelTypes from '../PointModelTypes.vue'
import { confirmState } from '@/composables/useConfirm'
import type { ItemType, PointModel } from '../pointModel'

afterEach(() => {
  confirmState.settle(false)
  document.body.innerHTML = ''
})

async function remove(w: ReturnType<typeof mount>, label: string, answer: boolean) {
  await w.find(`[aria-label="${label}"]`).trigger('click')
  expect(confirmState.open).toBe(true)
  expect(confirmState.title).toMatch(/^Remove this /)
  confirmState.settle(answer)
  await flushPromises()
}

describe('builder removals', () => {
  it('keeps an evidence type on cancel and removes it on confirm', async () => {
    const types: ItemType[] = [{ path: 'p' }]
    const w = mount(PointModelTypes, {
      props: { modelValue: types, base: 'b', diag: () => [] }
    })
    await remove(w, 'Remove evidence type', false)
    expect(types).toHaveLength(1)
    await remove(w, 'Remove evidence type', true)
    expect(types).toHaveLength(0)
  })

  it('asks before removing a section or a category', async () => {
    const model: PointModel = {
      sections: [{ key: 'genetic', categories: [{ key: 'probands', types: [] }] }],
      bands: []
    }
    const w = mount(PointModelSections, {
      props: { modelValue: model, diag: () => [], count: () => 0 }
    })
    ;(w.vm as unknown as { openSections: number[] }).openSections = [0]
    await flushPromises()
    await remove(w, 'Remove category', true)
    expect(model.sections[0]!.categories).toHaveLength(0)
    await remove(w, 'Remove section', false)
    expect(model.sections).toHaveLength(1)
  })
})
