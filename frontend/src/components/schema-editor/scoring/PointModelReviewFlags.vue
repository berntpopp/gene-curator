<template>
  <div>
    <p class="text-body-small text-medium-emphasis mb-4">
      Flags never change the score; they tell the reviewer where to look. Leave a flag blank to turn
      it off.
    </p>
    <v-row dense>
      <v-col cols="12" md="4">
        <v-text-field
          :model-value="flags.band_margin ?? ''"
          label="Band edge margin (points)"
          type="number"
          density="compact"
          variant="outlined"
          hint="Flag totals within this many points of a band minimum"
          persistent-hint
          :error-messages="diag(`${FLAGS}.band_margin`)"
          @update:model-value="v => update(f => setNumber(f, 'band_margin', v))"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-text-field
          :model-value="flags.hotspot?.max_variants ?? ''"
          label="Hotspot: at most N variants"
          type="number"
          density="compact"
          variant="outlined"
          :error-messages="diag(`${FLAGS}.hotspot.max_variants`)"
          @update:model-value="v => setHotspot('max_variants', v)"
        />
        <v-text-field
          :model-value="flags.hotspot?.min_share ?? ''"
          label="Hotspot: share of case points (0-1)"
          type="number"
          step="0.05"
          density="compact"
          variant="outlined"
          hint="e.g. 2 variants holding 0.5 of the case points"
          persistent-hint
          :error-messages="diag(`${FLAGS}.hotspot.min_share`).concat(diag(`${FLAGS}.hotspot`))"
          @update:model-value="v => setHotspot('min_share', v)"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-select
          :model-value="pair[0]"
          :items="sectionKeys"
          label="Experimental section"
          density="compact"
          variant="outlined"
          clearable
          @update:model-value="v => setPair(0, v)"
        />
        <v-select
          :model-value="pair[1]"
          :items="sectionKeys"
          label="Outscores genetic section"
          density="compact"
          variant="outlined"
          clearable
          :error-messages="diag(`${FLAGS}.experimental_over_genetic`)"
          @update:model-value="v => setPair(1, v)"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import {
    MODEL_PATH,
    setNumber,
    type DiagFn,
    type PointModel,
    type ReviewFlags
  } from './pointModel'

  defineProps<{ diag: DiagFn }>()
  const model = defineModel<PointModel>({ required: true })
  const FLAGS = `${MODEL_PATH}.review_flags`

  const flags = computed(() => model.value.review_flags ?? {})
  const pair = computed(() => flags.value.experimental_over_genetic ?? [])
  const sectionKeys = computed(() => model.value.sections.map(s => s.key).filter(Boolean))

  /** Edit a copy, then store it, or drop `review_flags` when nothing is left. */
  const update = (edit: (f: ReviewFlags) => void) => {
    const next = { ...flags.value }
    edit(next)
    if (Object.keys(next).length) model.value.review_flags = next
    else delete model.value.review_flags
  }

  const setHotspot = (key: 'max_variants' | 'min_share', value: unknown) =>
    update(f => {
      const hotspot: Record<string, number> = { ...(f.hotspot ?? {}) }
      setNumber(hotspot, key, value)
      if (Object.keys(hotspot).length) f.hotspot = hotspot as ReviewFlags['hotspot']
      else delete f.hotspot
    })

  const setPair = (at: 0 | 1, value: string | null) =>
    update(f => {
      const next = [...pair.value]
      next[at] = value ?? ''
      if (next.some(Boolean)) f.experimental_over_genetic = next
      else delete f.experimental_over_genetic
    })
</script>
