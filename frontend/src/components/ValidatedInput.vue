<template>
  <v-text-field
    v-model="internalValue"
    :label="label"
    :hint="hint"
    :loading="isValidating"
    :error-messages="errorMessages"
    :messages="successMessages"
    :prepend-inner-icon="statusIcon"
    :color="statusColor"
    :required="required"
    @blur="handleBlur"
  >
    <template #append-inner>
      <v-tooltip v-if="result && result.data" location="top">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small">mdi-information</v-icon>
        </template>
        <div class="text-caption">
          <div v-if="validator === 'hgnc'">
            <strong>{{ result.data.approved_symbol }}</strong>
            <div>{{ result.data.hgnc_id }}</div>
            <div v-if="result.data.locus_type">Type: {{ result.data.locus_type }}</div>
          </div>
          <div v-else-if="validator === 'pubmed'">
            <strong>{{ result.data.title }}</strong>
            <div>{{ result.data.journal }} ({{ result.data.pub_date }})</div>
          </div>
          <div v-else-if="validator === 'hpo'">
            <strong>{{ result.data.term_name }}</strong>
            <div class="text-caption">{{ result.data.definition }}</div>
          </div>
        </div>
      </v-tooltip>
    </template>

    <template v-if="result && result.suggestions" #append>
      <v-menu>
        <template #activator="{ props }">
          <v-btn v-bind="props" variant="text" size="small" color="warning"> Suggestions </v-btn>
        </template>
        <v-list>
          <v-list-item
            v-for="suggestion in result.suggestions.did_you_mean"
            :key="suggestion"
            @click="internalValue = suggestion"
          >
            <v-list-item-title>{{ suggestion }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
  import { computed, watch, type Ref } from 'vue'
  import { useValidation } from '@/composables/useValidation'
  import { useLogger } from '@/composables/useLogger'

  // useValidation() is still JavaScript; this is the shape the template and handlers rely on.
  interface ValidationResult {
    is_valid: boolean
    error_message?: string | null
    data?: Record<string, unknown> | null
    suggestions?: { did_you_mean?: string[] } | null
  }

  const props = withDefaults(
    defineProps<{
      modelValue: string
      validator: 'hgnc' | 'pubmed' | 'hpo'
      label: string
      hint?: string
      required?: boolean
    }>(),
    {
      hint: '',
      required: false
    }
  )

  const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

  const logger = useLogger()

  const {
    value: internalValue,
    result,
    isValidating,
    error
  } = useValidation(props.validator) as {
    value: Ref<string>
    result: Ref<ValidationResult | null>
    isValidating: Ref<boolean>
    error: Ref<string | null>
  }

  // Sync with v-model
  internalValue.value = props.modelValue

  // Watch for changes from parent
  watch(
    () => props.modelValue,
    newValue => {
      if (newValue !== internalValue.value) {
        internalValue.value = newValue
      }
    }
  )

  // Watch for internal changes and emit to parent
  watch(internalValue, newValue => {
    emit('update:modelValue', newValue)
  })

  // Emit on blur
  const handleBlur = () => {
    emit('update:modelValue', internalValue.value)
    logger.debug('Validated input blur', {
      validator: props.validator,
      value: internalValue.value,
      isValid: result.value?.is_valid
    })
  }

  // Status icon based on validation state
  const statusIcon = computed(() => {
    if (isValidating.value) return 'mdi-loading mdi-spin'
    if (result.value?.is_valid) return 'mdi-check-circle'
    if (result.value && !result.value.is_valid) return 'mdi-alert-circle'
    return ''
  })

  // Color based on validation state
  const statusColor = computed(() => {
    if (result.value?.is_valid) return 'success'
    if (result.value && !result.value.is_valid) return 'error'
    return ''
  })

  // Error messages
  const errorMessages = computed(() => {
    if (error.value) return [error.value]
    if (result.value && !result.value.is_valid && result.value.error_message) {
      return [result.value.error_message]
    }
    return []
  })

  // Success messages
  const successMessages = computed(() => {
    if (result.value?.is_valid && result.value.data) {
      if (props.validator === 'hgnc') {
        return [`✓ Approved symbol: ${result.value.data.approved_symbol}`]
      } else if (props.validator === 'pubmed') {
        return ['✓ Valid PMID']
      } else if (props.validator === 'hpo') {
        return [`✓ ${result.value.data.term_name}`]
      }
    }
    return []
  })
</script>
