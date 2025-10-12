module.exports = {
  root: true,
  env: {
    node: true,
    es2022: true,
    browser: true
  },
  extends: ['eslint:recommended', 'plugin:vue/vue3-recommended', '@vue/eslint-config-prettier'],
  plugins: ['vue'],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    // Vue.js specific rules
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

    // General JavaScript rules
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'prefer-const': 'error',
    'no-var': 'error',
    'object-shorthand': 'error',
    'prefer-template': 'error',
    'template-curly-spacing': 'error',
    'arrow-spacing': 'error',
    'comma-dangle': ['error', 'never'],
    quotes: ['error', 'single', { avoidEscape: true }],
    semi: ['error', 'never']
  },
  ignorePatterns: [
    'dist/**',
    'node_modules/**',
    '.output/**',
    'coverage/**',
    '*.config.js',
    '*.config.ts'
  ]
}
