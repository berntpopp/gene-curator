/** InviteMemberDialog role select slots with real Vuetify (Vuetify 4 slot `item` is the raw option). */
import { describe, it, expect, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { VSelect } from 'vuetify/components'
import InviteMemberDialog from '../InviteMemberDialog.vue'

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('InviteMemberDialog slots', () => {
  it('shows the role title and description in the menu and the selected role chip', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    wrapper = mount(InviteMemberDialog, {
      props: { modelValue: true, scopeId: 'scope-1' },
      global: { plugins: [pinia], stubs: { UserSearchAutocomplete: true } },
      attachTo: document.body
    })
    await flushPromises()
    expect(document.body.querySelector('.v-field .v-chip')?.textContent).toContain('Viewer')

    wrapper.findComponent(VSelect).vm.menu = true
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('Create and edit curations')
    expect(text).toContain('Review and approve curations')
  })
})
