import { describe, it, expect, vi } from 'vitest'
import { logService } from '@/services/logService'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import { VIcon } from 'vuetify/components'
import { icons } from '../icons'
import { mdiPaths } from '../iconPaths'

const render = (icon: string) =>
  mount(VIcon, { props: { icon }, global: { plugins: [createVuetify({ icons })] } })

describe('svg icon set', () => {
  it('renders the svg path for an mdi-* name', () => {
    expect(render('mdi-alert').find('path').attributes('d')).toBe(mdiPaths['mdi-alert'])
  })

  it('keeps extra classes such as mdi-spin', () => {
    const w = render('mdi-loading mdi-spin')
    expect(w.find('path').attributes('d')).toBe(mdiPaths['mdi-loading'])
    expect(w.classes()).toContain('mdi-spin')
  })

  it('passes unknown strings (Vuetify $aliases are svg paths) through', () => {
    expect(render('M0 0h1').find('path').attributes('d')).toBe('M0 0h1')
  })

  it('falls back to a placeholder and warns once for an unknown mdi-* name', () => {
    const warn = vi.spyOn(logService, 'warn').mockImplementation(() => {})
    const d = () => render('mdi-not-a-real-icon').find('path').attributes('d')
    expect(d()).toBe(mdiPaths['mdi-help-circle-outline'])
    d()
    expect(warn).toHaveBeenCalledTimes(1)
  })
})
