<template>
  <v-snackbar
    v-model="show"
    :color="color"
    :timeout="timeout"
    :location="location"
    :multi-line="multiLine"
  >
    <div class="d-flex align-center">
      <v-icon v-if="icon" :icon="icon" class="mr-3" />
      <span>{{ message }}</span>
    </div>

    <template #actions>
      <v-btn variant="text" @click="close"> Close </v-btn>
    </template>
  </v-snackbar>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'

  // Props
  const props = withDefaults(
    defineProps<{
      modelValue?: boolean
      message?: string
      color?: string
      timeout?: number
      location?: 'top' | 'bottom' | 'left' | 'right' | 'start' | 'end'
      multiLine?: boolean
    }>(),
    {
      modelValue: false,
      message: '',
      color: 'info',
      timeout: 5000,
      location: 'bottom',
      multiLine: false
    }
  )

  // Emits
  const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    close: []
  }>()

  // State
  const show = ref(props.modelValue)

  // Icon mapping based on color
  const iconMap: Record<string, string> = {
    success: 'mdi-check-circle',
    error: 'mdi-alert-circle',
    warning: 'mdi-alert',
    info: 'mdi-information'
  }

  const icon = ref(iconMap[props.color] || 'mdi-information')

  // Watchers
  watch(
    () => props.modelValue,
    newVal => {
      show.value = newVal
    }
  )

  watch(
    () => props.color,
    newColor => {
      icon.value = iconMap[newColor] || 'mdi-information'
    }
  )

  watch(show, newVal => {
    emit('update:modelValue', newVal)
  })

  // Methods
  const close = () => {
    show.value = false
    emit('close')
  }
</script>

<style scoped>
  /* Add any custom styles here */
</style>
