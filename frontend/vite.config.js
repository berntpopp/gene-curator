import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: parseInt(process.env.VITE_DEV_PORT || process.env.PORT || '3000'),
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8051',
        changeOrigin: true,
        secure: false
      }
    },
    watch: {
      usePolling: !!process.env.DOCKER_POLLING
    },
    hmr: {
      overlay: true
    }
  },
  build: {
    outDir: 'dist'
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.js'],
    css: true,
    server: {
      deps: {
        inline: ['vuetify']
      }
    },
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/tests/e2e/**'
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.spec.js'
      ]
    }
  }
})
