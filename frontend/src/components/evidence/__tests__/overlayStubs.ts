import { vi } from 'vitest'

/**
 * Vuetify overlays (menus, tooltips, autocomplete lists) read window.visualViewport,
 * which happy-dom does not provide. Call from beforeEach in specs that open overlays.
 */
export function stubVisualViewport(): void {
  vi.stubGlobal('visualViewport', {
    width: 1024,
    height: 768,
    scale: 1,
    offsetLeft: 0,
    offsetTop: 0,
    pageLeft: 0,
    pageTop: 0,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  })
}
