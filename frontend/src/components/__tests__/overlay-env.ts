/**
 * Test helper for Vuetify overlays (v-dialog, v-snackbar).
 * happy-dom does not implement window.visualViewport, which the overlays read on open.
 */
export function installVisualViewport(): void {
  if (!('visualViewport' in window)) {
    Object.defineProperty(window, 'visualViewport', {
      configurable: true,
      value: {
        width: 1024,
        height: 768,
        scale: 1,
        offsetLeft: 0,
        offsetTop: 0,
        pageLeft: 0,
        pageTop: 0,
        addEventListener: () => {},
        removeEventListener: () => {}
      }
    })
  }
}
