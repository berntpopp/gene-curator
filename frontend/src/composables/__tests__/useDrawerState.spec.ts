import { describe, it, expect, beforeEach } from 'vitest'
import { useDrawerState, useGlobalDrawerState } from '../useDrawerState'

describe('useDrawerState', () => {
  beforeEach(() => {
    useGlobalDrawerState().closeAll()
  })

  it('throws when no drawer id is given', () => {
    expect(() => useDrawerState('')).toThrow('useDrawerState requires a unique drawerId')
  })

  it('opens and closes a single drawer', () => {
    const drawer = useDrawerState('drawer-a')

    expect(drawer.isOpen.value).toBe(false)
    drawer.open()
    expect(drawer.isOpen.value).toBe(true)
    drawer.close()
    expect(drawer.isOpen.value).toBe(false)
  })

  it('opening one drawer closes the previously open one', () => {
    const first = useDrawerState('drawer-first')
    const second = useDrawerState('drawer-second')

    first.open()
    second.open()

    expect(first.isOpen.value).toBe(false)
    expect(second.isOpen.value).toBe(true)
  })

  it('toggle flips the drawer state', () => {
    const drawer = useDrawerState('drawer-toggle')

    drawer.toggle()
    expect(drawer.isOpen.value).toBe(true)
    drawer.toggle()
    expect(drawer.isOpen.value).toBe(false)
  })

  it('close does nothing when another drawer is open', () => {
    const mine = useDrawerState('drawer-mine')
    const other = useDrawerState('drawer-other')

    other.open()
    mine.close()

    expect(other.isOpen.value).toBe(true)
  })

  it('setting isOpen via v-model updates the active drawer', () => {
    const drawer = useDrawerState('drawer-model')

    drawer.isOpen.value = true
    expect(drawer.isOpen.value).toBe(true)

    drawer.isOpen.value = false
    expect(drawer.isOpen.value).toBe(false)
  })

  it('setting isOpen to false on an inactive drawer keeps the active one open', () => {
    const active = useDrawerState('drawer-active')
    const idle = useDrawerState('drawer-idle')

    active.open()
    idle.isOpen.value = false

    expect(active.isOpen.value).toBe(true)
  })

  it('exposes the drawer id as readonly ref', () => {
    const drawer = useDrawerState('drawer-id')

    expect(drawer.drawerId.value).toBe('drawer-id')
  })

  it('global helpers report open state and registered drawers', () => {
    const global = useGlobalDrawerState()
    const drawer = useDrawerState('drawer-global')

    expect(global.hasOpenDrawer.value).toBe(false)
    drawer.open()
    expect(global.hasOpenDrawer.value).toBe(true)
    expect(global.getActiveDrawer.value).toBe('drawer-global')
    expect(global.getRegisteredDrawers.value).toContain('drawer-global')

    global.closeAll()
    expect(global.hasOpenDrawer.value).toBe(false)
    expect(global.getActiveDrawer.value).toBeNull()
  })
})
