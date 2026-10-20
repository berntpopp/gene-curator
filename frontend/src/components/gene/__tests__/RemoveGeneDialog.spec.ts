import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RemoveGeneDialog from '../RemoveGeneDialog.vue'

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

function mountDialog(props: Record<string, unknown> = {}) {
  return mount(RemoveGeneDialog, {
    props: { modelValue: true, geneSymbol: 'BRCA1', isRemoving: false, ...props },
    global: { stubs: { VDialog: dialogStub } }
  })
}

describe('RemoveGeneDialog', () => {
  it('names the gene and explains that the catalogue entry is kept', () => {
    const wrapper = mountDialog()

    expect(wrapper.text()).toContain('Remove Gene from Scope')
    expect(wrapper.text()).toContain('BRCA1')
    expect(wrapper.text()).toContain('will not delete the gene from the catalog')
  })

  it('emits confirm and cancel from the buttons', async () => {
    const wrapper = mountDialog()

    await wrapper
      .findAll('button')
      .find(b => b.text().trim() === 'Remove')!
      .trigger('click')
    await wrapper
      .findAll('button')
      .find(b => b.text().trim() === 'Cancel')!
      .trigger('click')

    expect(wrapper.emitted('confirm')).toHaveLength(1)
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('disables cancel while the removal is in progress', () => {
    const wrapper = mountDialog({ isRemoving: true })

    const cancel = wrapper.findAll('button').find(b => b.text().trim() === 'Cancel')!
    expect(cancel.attributes('disabled')).toBeDefined()
  })
})
