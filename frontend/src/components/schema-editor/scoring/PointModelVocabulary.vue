<template>
  <div>
    <div class="text-title-small mb-1">Classification vocabulary</div>
    <p class="text-body-small text-medium-emphasis mb-2">
      The classes this methodology reports, in display order. Without a list the ClinGen classes
      apply. The tone picks the colour.
    </p>
    <div v-for="(item, i) in items ?? []" :key="i" class="d-flex ga-2 align-start">
      <v-text-field
        v-model="item.key"
        label="Key"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${PATH}[${i}].key`)"
      />
      <v-text-field
        v-model="item.label"
        label="Label"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${PATH}[${i}].label`)"
      />
      <v-text-field
        :model-value="item.order"
        label="Order"
        type="number"
        density="compact"
        variant="outlined"
        class="order"
        :error-messages="diag(`${PATH}[${i}].order`)"
        @update:model-value="v => (item.order = Number(v))"
      />
      <v-select
        v-model="item.tone"
        :items="TONES"
        label="Tone"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${PATH}[${i}].tone`)"
      />
      <v-btn
        aria-label="Remove class"
        icon="mdi-close"
        size="small"
        variant="text"
        @click="remove(i)"
      />
    </div>
    <v-alert
      v-for="msg in diag(PATH)"
      :key="msg"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-2"
      :text="msg"
    />
    <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="add">Class</v-btn>
  </div>
</template>

<script setup lang="ts">
  import { TONES, type Classification, type DiagFn } from './pointModel'

  defineProps<{ diag: DiagFn }>()
  const items = defineModel<Classification[] | undefined>()
  const PATH = 'scoring_configuration.classifications'

  const add = () => {
    const list = items.value ?? []
    items.value = [...list, { key: '', label: '', order: list.length + 1, tone: 'limited' }]
  }
  // An empty list would mean "no classes", so the last removal drops the key (ClinGen default)
  const remove = (i: number) => {
    const rest = (items.value ?? []).filter((_, k) => k !== i)
    items.value = rest.length ? rest : undefined
  }
</script>

<style scoped>
  .order {
    max-width: 96px;
  }
</style>
