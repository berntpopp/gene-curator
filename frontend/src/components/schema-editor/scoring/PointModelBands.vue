<template>
  <div>
    <div class="text-title-small mb-1">Bands</div>
    <p class="text-body-small text-medium-emphasis mb-2">
      Checked top to bottom; the first band the total reaches wins. Minimums must not increase down
      the list.
    </p>
    <v-alert
      v-for="msg in diag(`${MODEL_PATH}.bands`)"
      :key="msg"
      type="error"
      variant="tonal"
      density="compact"
      class="mb-2"
      :text="msg"
    />
    <v-table density="compact">
      <thead>
        <tr>
          <th>Class</th>
          <th class="num">Min total</th>
          <th v-for="key in sectionKeys" :key="key" class="num">Min {{ key }}</th>
          <th>Requires (true field)</th>
          <th aria-label="Actions" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="(band, i) in model.bands" :key="i">
          <td>
            <v-combobox
              v-model="band.class"
              :items="classKeys"
              aria-label="Band class"
              density="compact"
              variant="plain"
              :error-messages="diag(`${bandPath(i)}.class`)"
              :hide-details="!diag(`${bandPath(i)}.class`).length"
            />
          </td>
          <td class="num">
            <v-text-field
              :model-value="band.min ?? ''"
              aria-label="Minimum total"
              type="number"
              density="compact"
              variant="plain"
              :error-messages="diag(`${bandPath(i)}.min`)"
              :hide-details="!diag(`${bandPath(i)}.min`).length"
              @update:model-value="v => setNumber(band, 'min', v)"
            />
          </td>
          <td v-for="key in sectionKeys" :key="key" class="num">
            <v-text-field
              :model-value="band.section_min?.[key] ?? ''"
              :aria-label="`Minimum ${key}`"
              type="number"
              density="compact"
              variant="plain"
              :error-messages="diag(`${bandPath(i)}.section_min.${key}`)"
              :hide-details="!diag(`${bandPath(i)}.section_min.${key}`).length"
              @update:model-value="v => setSectionMin(band, key, v)"
            />
          </td>
          <td>
            <v-text-field
              :model-value="band.requires ?? ''"
              aria-label="Requires field"
              density="compact"
              variant="plain"
              placeholder="replicated_over_time"
              :error-messages="diag(`${bandPath(i)}.requires`)"
              :hide-details="!diag(`${bandPath(i)}.requires`).length"
              @update:model-value="v => setText(band, 'requires', v)"
            />
          </td>
          <td class="text-no-wrap">
            <v-btn
              aria-label="Move band up"
              icon="mdi-chevron-up"
              size="small"
              variant="text"
              :disabled="i === 0"
              @click="move(i, -1)"
            />
            <v-btn
              aria-label="Move band down"
              icon="mdi-chevron-down"
              size="small"
              variant="text"
              :disabled="i === model.bands.length - 1"
              @click="move(i, 1)"
            />
            <v-btn
              aria-label="Remove band"
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="model.bands.splice(i, 1)"
            />
          </td>
        </tr>
      </tbody>
    </v-table>
    <v-btn
      size="small"
      variant="text"
      prepend-icon="mdi-plus"
      @click="model.bands.push({ class: '' })"
    >
      Band
    </v-btn>

    <div class="text-title-small mt-6 mb-1">Overrides</div>
    <p class="text-body-small text-medium-emphasis mb-2">
      Win over the bands when the evidence field has content (optionally only rows whose column
      holds one of the values), e.g. contradictory evidence that disputes the relationship.
    </p>
    <div v-for="(o, i) in model.overrides ?? []" :key="i" class="d-flex ga-2 align-start">
      <v-text-field
        v-model="o.when"
        label="Evidence field"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${MODEL_PATH}.overrides[${i}].when`)"
      />
      <v-text-field
        :model-value="o.field ?? ''"
        label="Row column"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${MODEL_PATH}.overrides[${i}].field`)"
        @update:model-value="v => setText(o, 'field', v)"
      />
      <v-combobox
        :model-value="(o.in ?? []).map(String)"
        label="Is one of"
        multiple
        chips
        closable-chips
        density="compact"
        variant="outlined"
        :error-messages="diag(`${MODEL_PATH}.overrides[${i}].in`)"
        @update:model-value="v => setIn(o, v)"
      />
      <v-combobox
        v-model="o.class"
        :items="classKeys"
        label="Class"
        density="compact"
        variant="outlined"
        :error-messages="diag(`${MODEL_PATH}.overrides[${i}].class`)"
      />
      <v-btn
        aria-label="Remove override"
        icon="mdi-close"
        size="small"
        variant="text"
        @click="removeOverride(i)"
      />
    </div>
    <v-btn size="small" variant="text" prepend-icon="mdi-plus" @click="addOverride">Override</v-btn>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import {
    MODEL_PATH,
    keepTypes,
    setNumber,
    setText,
    type Band,
    type DiagFn,
    type Override,
    type PointModel
  } from './pointModel'

  defineProps<{ diag: DiagFn; classKeys: string[] }>()
  const model = defineModel<PointModel>({ required: true })

  const sectionKeys = computed(() => model.value.sections.map(s => s.key).filter(Boolean))
  const bandPath = (i: number) => `${MODEL_PATH}.bands[${i}]`

  const setSectionMin = (band: Band, key: string, value: unknown) => {
    const mins = { ...(band.section_min ?? {}) }
    if (value === '' || value === null) delete mins[key]
    else mins[key] = Number(value)
    if (Object.keys(mins).length) band.section_min = mins
    else delete band.section_min
  }

  const move = (i: number, by: number) => {
    const bands = model.value.bands
    const [band] = bands.splice(i, 1)
    if (band) bands.splice(i + by, 0, band)
  }

  // An empty list removes `in`; the validator then asks for it while `field` is set
  const setIn = (o: Override, values: unknown[]) => {
    if (values.length) o.in = keepTypes(o.in, values)
    else delete o.in
  }

  const addOverride = () => {
    model.value.overrides = [...(model.value.overrides ?? []), { when: '', class: 'disputed' }]
  }
  const removeOverride = (i: number) => {
    const rest = (model.value.overrides ?? []).filter((_, k) => k !== i)
    if (rest.length) model.value.overrides = rest
    else delete model.value.overrides
  }
</script>

<style scoped>
  .num {
    width: 104px;
  }
</style>
