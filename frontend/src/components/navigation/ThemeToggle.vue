<template>
  <v-tooltip :text="themeLabel" location="bottom">
    <template #activator="{ props }">
      <v-btn v-bind="props" :aria-label="themeLabel" icon variant="text" @click="toggleTheme">
        <v-icon>{{ MODE_ICON[mode] }}</v-icon>
      </v-btn>
    </template>
  </v-tooltip>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue'
  import { useTheme } from 'vuetify'
  import { useLogger } from '@/composables/useLogger'

  const logger = useLogger()
  const theme = useTheme()

  // Theme mode (persisted in localStorage, restored in main.ts before Vuetify init)
  type ThemeMode = 'light' | 'dark' | 'system'
  const NEXT_MODE: Record<ThemeMode, ThemeMode> = { system: 'light', light: 'dark', dark: 'system' }
  const MODE_ICON: Record<ThemeMode, string> = {
    system: 'mdi-theme-light-dark',
    light: 'mdi-white-balance-sunny',
    dark: 'mdi-weather-night'
  }
  const saved = localStorage.getItem('theme')
  const mode = ref<ThemeMode>(saved === 'light' || saved === 'dark' ? saved : 'system')

  const themeLabel = computed(
    () => `Theme: ${mode.value}. Switch to ${NEXT_MODE[mode.value]} theme`
  )

  /** Cycle system -> light -> dark -> system */
  const toggleTheme = () => {
    mode.value = NEXT_MODE[mode.value]
    void theme.change(mode.value)
    localStorage.setItem('theme', mode.value)
    logger.info('Theme changed', { theme: mode.value })
  }
</script>
