/**
 * Vitest Setup File
 *
 * Global configuration for all tests including:
 * - Vuetify plugin configuration
 * - Global test utilities
 * - Mock setup
 *
 * This file is automatically loaded before all tests via vite.config.js
 */

import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { vi } from 'vitest'
import axios from 'axios'

// Tests never touch the network: unmocked requests fail fast instead of hitting localhost:8051
axios.defaults.adapter = config =>
  Promise.reject(
    new Error(`Unmocked request in test: ${config.method?.toUpperCase()} ${config.url}`)
  )

// Create Vuetify instance for tests
const vuetify = createVuetify({
  components,
  directives
})

// Configure Vue Test Utils to use Vuetify
config.global.plugins = [vuetify]

// happy-dom lacks window.matchMedia, which Vuetify display utilities read
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // Deprecated
    removeListener: vi.fn(), // Deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// Vuetify overlays (dialogs, menus, selects) read visualViewport, which happy-dom does not provide
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
    addEventListener: () => undefined,
    removeEventListener: () => undefined
  }
})

// Mock IntersectionObserver (for Vuetify components)
vi.stubGlobal(
  'IntersectionObserver',
  class IntersectionObserver {
    constructor() {}
    disconnect() {}
    observe() {}
    takeRecords() {
      return []
    }
    unobserve() {}
  }
)

// Mock ResizeObserver (for Vuetify components)
vi.stubGlobal(
  'ResizeObserver',
  class ResizeObserver {
    constructor() {}
    disconnect() {}
    observe() {}
    unobserve() {}
  }
)

// Suppress Vuetify warnings in tests
globalThis.console.warn = vi.fn()
