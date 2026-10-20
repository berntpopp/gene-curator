import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { useResponsive, type UseResponsiveReturn } from '../useResponsive'

type ChangeListener = (e: { matches: boolean }) => void

function setWidth(width: number, height = 900): void {
  Object.defineProperty(window, 'innerWidth', { configurable: true, writable: true, value: width })
  Object.defineProperty(window, 'innerHeight', {
    configurable: true,
    writable: true,
    value: height
  })
}

function mountResponsive(custom?: Parameters<typeof useResponsive>[0]) {
  let api: UseResponsiveReturn | undefined
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useResponsive(custom)
        return () => h('div')
      }
    })
  )
  if (!api) throw new Error('composable not initialised')
  return { api, wrapper }
}

describe('useResponsive', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setWidth(1280)
  })

  it('classifies desktop widths by default (768 / 1024 breakpoints)', () => {
    const { api, wrapper } = mountResponsive()

    expect(api.windowWidth.value).toBe(1280)
    expect(api.isDesktop.value).toBe(true)
    expect(api.isMobile.value).toBe(false)
    expect(api.isTablet.value).toBe(false)
    expect(api.deviceType.value).toBe('desktop')
    wrapper.unmount()
  })

  it('classifies mobile and tablet widths', () => {
    setWidth(500)
    const mobile = mountResponsive()
    expect(mobile.api.deviceType.value).toBe('mobile')
    expect(mobile.api.isMobile.value).toBe(true)
    mobile.wrapper.unmount()

    setWidth(900)
    const tablet = mountResponsive()
    expect(tablet.api.deviceType.value).toBe('tablet')
    expect(tablet.api.isTablet.value).toBe(true)
    tablet.wrapper.unmount()
  })

  it('matches, atLeast and atMost compare against the breakpoints', () => {
    setWidth(900)
    const { api, wrapper } = mountResponsive()

    expect(api.matches('TABLET')).toBe(true)
    expect(api.matches('mobile')).toBe(false)
    expect(api.matches('unknown')).toBe(false)

    expect(api.atLeast('mobile')).toBe(true)
    expect(api.atLeast('tablet')).toBe(true)
    expect(api.atLeast('desktop')).toBe(false)
    expect(api.atLeast('nope')).toBe(false)

    expect(api.atMost('mobile')).toBe(false)
    expect(api.atMost('tablet')).toBe(true)
    expect(api.atMost('desktop')).toBe(true)
    expect(api.atMost('nope')).toBe(false)
    wrapper.unmount()
  })

  it('honours custom breakpoints', () => {
    setWidth(600)
    const { api, wrapper } = mountResponsive({ mobile: 480, tablet: 640 })

    expect(api.isTablet.value).toBe(true)
    expect(api.breakpoints.value).toEqual({ mobile: 480, tablet: 640 })
    wrapper.unmount()
  })

  it('reports orientation from the viewport size', () => {
    setWidth(400, 800)
    const portrait = mountResponsive()
    expect(portrait.api.isPortrait.value).toBe(true)
    expect(portrait.api.isLandscape.value).toBe(false)
    portrait.wrapper.unmount()

    setWidth(800, 400)
    const landscape = mountResponsive()
    expect(landscape.api.isLandscape.value).toBe(true)
    landscape.wrapper.unmount()
  })

  it('detects touch devices via touch points', () => {
    const original = navigator.maxTouchPoints
    Object.defineProperty(navigator, 'maxTouchPoints', { configurable: true, value: 5 })
    const { api, wrapper } = mountResponsive()

    expect(api.isTouchDevice.value).toBe(true)

    Object.defineProperty(navigator, 'maxTouchPoints', { configurable: true, value: original })
    wrapper.unmount()
  })

  it('falls back to resize events when matchMedia is unavailable', () => {
    const original = window.matchMedia
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: undefined
    })
    const addSpy = vi.spyOn(window, 'addEventListener')
    const removeSpy = vi.spyOn(window, 'removeEventListener')

    const { api, wrapper } = mountResponsive()
    expect(addSpy).toHaveBeenCalledWith('resize', expect.any(Function))

    setWidth(400)
    window.dispatchEvent(new Event('resize'))
    expect(api.windowWidth.value).toBe(400)

    wrapper.unmount()
    expect(removeSpy).toHaveBeenCalledWith('resize', expect.any(Function))

    addSpy.mockRestore()
    removeSpy.mockRestore()
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: original
    })
  })

  it('registers media query listeners on mount and updates width on change', () => {
    const { wrapper } = mountResponsive()
    const matchMedia = window.matchMedia as Mock
    expect(matchMedia).toHaveBeenCalledTimes(3)

    const mobileQuery = matchMedia.mock.results[0]?.value as {
      addEventListener: Mock
      removeEventListener: Mock
    }
    const listener = mobileQuery.addEventListener.mock.calls[0]?.[1] as ChangeListener

    setWidth(300)
    listener({ matches: false })
    expect(mobileQuery.addEventListener).toHaveBeenCalledWith('change', expect.any(Function))

    listener({ matches: true })
    wrapper.unmount()

    expect(mobileQuery.removeEventListener).toHaveBeenCalledWith('change', listener)
  })
})
