import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import prettier from '@vue/eslint-config-prettier'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import globals from 'globals'

export default defineConfigWithVueTs(
  {
    ignores: [
      'dist/**',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
      'src/types/api.generated.ts'
    ]
  },
  js.configs.recommended,
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  prettier,
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.node }
    },
    rules: {
      'vue/multi-word-component-names': 'warn',
      'vue/no-unused-vars': 'error',
      'vue/component-definition-name-casing': ['error', 'PascalCase'],
      'vue/component-name-in-template-casing': ['error', 'PascalCase'],
      'vue/prop-name-casing': ['error', 'camelCase'],
      'vue/attribute-hyphenation': ['error', 'always'],
      'vue/v-bind-style': ['error', 'shorthand'],
      'vue/v-on-style': ['error', 'shorthand'],
      'vue/require-default-prop': 'warn',
      'vue/require-prop-types': 'error',
      'vue/no-v-html': 'warn',
      'vue/valid-v-slot': ['error', { allowModifiers: true }],
      // TS migration in progress: flip to 'error' once every SFC uses <script setup lang="ts">
      'vue/block-lang': 'off',
      // Use useLogger()/logService (AGENTS.md); only the logging layer may touch console
      'no-console': 'error',
      'no-debugger': 'error',
      // ESLint 9 started flagging unused catch bindings; keep the v8 behaviour
      '@typescript-eslint/no-unused-vars': ['error', { caughtErrors: 'none' }],
      'prefer-const': 'error',
      'no-var': 'error',
      'object-shorthand': 'error',
      'prefer-template': 'error'
    }
  },
  {
    files: [
      'src/services/logService.js',
      'src/plugins/logger.js',
      'src/stores/logStore.js',
      'src/utils/logSanitizer.js',
      'src/test/**',
      '**/__tests__/**',
      'scripts/**',
      'tests/**',
      '*.config.js'
    ],
    languageOptions: { globals: { ...globals.vitest } },
    rules: { 'no-console': 'off' }
  }
)
