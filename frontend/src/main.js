import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Logging system
import loggerPlugin from './plugins/logger'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// Material Design Icons
import '@mdi/font/css/materialdesignicons.css'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        colors: {
          primary: '#1976D2',
          secondary: '#424242',
          accent: '#82B1FF',
          error: '#FF5252',
          info: '#2196F3',
          success: '#4CAF50',
          warning: '#FFC107'
        }
      }
    }
  }
})

const app = createApp(App)
const pinia = createPinia()

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
