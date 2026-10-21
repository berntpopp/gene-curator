import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Logging system
import loggerPlugin from './plugins/logger'

// Pinia error handling plugin
import { piniaErrorHandlerPlugin } from './plugins/piniaErrorHandler'

// Vuetify
import 'vuetify/styles'
import '@fontsource/ibm-plex-sans/400.css'
import '@fontsource/ibm-plex-sans/600.css'
import '@fontsource/ibm-plex-mono/400.css'
import { createVuetify, type ThemeDefinition } from 'vuetify'

// SVG icons (only the used mdi paths are bundled)
import { icons } from './plugins/icons'

// Theme: saved choice, else follow the OS (Vuetify resolves 'system' via prefers-color-scheme)
const savedTheme = localStorage.getItem('theme')

// Cool-grey neutrals share one hue family in both themes; navy is the only action colour.
// Classification (`cls-*`) is ordinal: strength is drawn as filled bars, only disputed/refuted get a hue.
const customLightTheme: ThemeDefinition = {
  dark: false,
  colors: {
    background: '#F4F5F7',
    surface: '#FFFFFF',
    'surface-bright': '#FFFFFF',
    'surface-light': '#F4F5F7',
    'surface-variant': '#EAEDF1',
    'on-surface': '#141A33',
    'on-surface-variant': '#565E70',
    primary: '#1E2A5E',
    'on-primary': '#FFFFFF',
    error: '#B3261E',
    info: '#0B7A83',
    success: '#1F7A4D',
    warning: '#9A5B00',
    'cls-definitive': '#141A33',
    'cls-strong': '#141A33',
    'cls-moderate': '#141A33',
    'cls-limited': '#141A33',
    'cls-no-known': '#565E70',
    'cls-disputed': '#9A5B00',
    'cls-refuted': '#B3261E'
  },
  variables: {
    'border-color': '#141A33',
    'border-opacity': 0.16,
    'high-emphasis-opacity': 0.87,
    'medium-emphasis-opacity': 0.68,
    'disabled-opacity': 0.38
  }
}

const customDarkTheme: ThemeDefinition = {
  dark: true,
  colors: {
    background: '#10131C',
    surface: '#171B27',
    'surface-bright': '#202636',
    'surface-light': '#202636',
    'surface-variant': '#1D2230',
    'on-surface': '#E6E8EE',
    'on-surface-variant': '#A3AABA',
    primary: '#A9B8F2',
    'on-primary': '#10131C',
    error: '#F2958E',
    info: '#5CC4CC',
    success: '#6CC596',
    warning: '#E8B35A',
    'cls-definitive': '#E6E8EE',
    'cls-strong': '#E6E8EE',
    'cls-moderate': '#E6E8EE',
    'cls-limited': '#E6E8EE',
    'cls-no-known': '#A3AABA',
    'cls-disputed': '#E8B35A',
    'cls-refuted': '#F2958E'
  },
  variables: {
    'border-color': '#FFFFFF',
    'border-opacity': 0.14,
    'high-emphasis-opacity': 0.87,
    'medium-emphasis-opacity': 0.68,
    'disabled-opacity': 0.38
  }
}

const vuetify = createVuetify({
  icons,
  // Vuetify 4 lowered the defaults; keep v3 breakpoints so layouts do not shift.
  display: { thresholds: { md: 960, lg: 1280, xl: 1920, xxl: 2560 } },
  // Buttons and tabs keep the case written in code (Vuetify uppercases them by default).
  defaults: {
    VBtn: { class: 'text-none' },
    VTab: { class: 'text-none' }
  },
  theme: {
    defaultTheme: savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : 'system',
    themes: {
      light: customLightTheme,
      dark: customDarkTheme
    }
  }
})

const app = createApp(App)
const pinia = createPinia()

// Add Pinia plugins
pinia.use(piniaErrorHandlerPlugin)

// Install plugins in order:
// 1. Pinia (state management) - must be first
// 2. Logger (requires Pinia)
// 3. Router
// 4. Vuetify
app.use(pinia)
app.use(loggerPlugin)
app.use(router)
app.use(vuetify)

app.mount('#app')
