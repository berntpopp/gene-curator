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
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Material Design Icons
import '@mdi/font/css/materialdesignicons.css'

// Theme: read saved preference before creating Vuetify (avoids flash)
const savedTheme = localStorage.getItem('theme') || 'dark'

const customLightTheme = {
  dark: false,
  colors: {
    background: '#F5F5F9',
    surface: '#FFFFFF',
    'surface-bright': '#FFFFFF',
    'surface-light': '#EEEEEE',
    'surface-variant': '#E0E0E6',
    'on-surface-variant': '#424242',
    primary: '#1976D2',
    'primary-darken-1': '#1565C0',
    secondary: '#546E7A',
    'secondary-darken-1': '#37474F',
    accent: '#82B1FF',
    error: '#D32F2F',
    info: '#1976D2',
    success: '#388E3C',
    warning: '#F57C00',
  },
  variables: {
    'border-color': '#000000',
    'border-opacity': 0.12,
    'high-emphasis-opacity': 0.87,
    'medium-emphasis-opacity': 0.60,
    'disabled-opacity': 0.38,
  },
}

const customDarkTheme = {
  dark: true,
  colors: {
    background: '#1A1A2E',
    surface: '#25253A',
    'surface-bright': '#32324A',
    'surface-light': '#2D2D42',
    'surface-variant': '#43435A',
    'on-surface-variant': '#C8C8D8',
    primary: '#5C9CE6',
    'primary-darken-1': '#1565C0',
    secondary: '#78909C',
    'secondary-darken-1': '#546E7A',
    accent: '#82B1FF',
    error: '#EF5350',
    info: '#42A5F5',
    success: '#66BB6A',
    warning: '#FFA726',
  },
  variables: {
    'border-color': '#FFFFFF',
    'border-opacity': 0.12,
    'high-emphasis-opacity': 0.87,
    'medium-emphasis-opacity': 0.60,
    'disabled-opacity': 0.38,
  },
}

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: savedTheme === 'light' ? 'light' : 'dark',
    themes: {
      light: customLightTheme,
      dark: customDarkTheme,
    },
  },
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
