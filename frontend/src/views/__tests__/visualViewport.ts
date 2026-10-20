// Vuetify overlays (dialogs, menus, selects) read visualViewport, which happy-dom does not provide.
// Import for the side effect.
if (!('visualViewport' in window)) {
  Object.defineProperty(window, 'visualViewport', {
    value: {
      width: 1024,
      height: 768,
      scale: 1,
      offsetLeft: 0,
      offsetTop: 0,
      pageLeft: 0,
      pageTop: 0,
      addEventListener: () => undefined,
      removeEventListener: () => undefined
    }
  })
}

export {}
