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

// Create Vuetify instance for tests
const vuetify = createVuetify({
  components,
  directives
})

// Configure Vue Test Utils to use Vuetify
config.global.plugins = [vuetify]

// Mock window.matchMedia (for useResponsive tests)
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

// Mock IntersectionObserver (for Vuetify components)
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return []
  }
  unobserve() {}
}

// Mock ResizeObserver (for Vuetify components)
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
}

// Suppress Vuetify warnings in tests
global.console.warn = vi.fn()
