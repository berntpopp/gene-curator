<template>
  <div>
    <v-text-field
      :model-value="model.total_cap ?? ''"
      label="Total cap"
      type="number"
      density="compact"
      variant="outlined"
      class="total-cap mb-2"
      hint="Blank means no cap on the total"
      :error-messages="diag(`${MODEL_PATH}.total_cap`)"
      @update:model-value="v => setNumber(model, 'total_cap', v)"
    />
    <v-expansion-panels v-model="openSections" multiple variant="accordion">
      <v-expansion-panel v-for="(section, i) in model.sections" :key="i" :value="i">
        <v-expansion-panel-title>
          <span class="font-weight-medium">{{ section.key || 'New section' }}</span>
          <span class="text-medium-emphasis ml-3">
            {{ section.categories.length }} categories
            <template v-if="section.cap !== undefined"> · cap {{ section.cap }}</template>
          </span>
          <v-badge
            v-if="count(`${MODEL_PATH}.sections[${i}]`)"
            :content="count(`${MODEL_PATH}.sections[${i}]`)"
            color="error"
            inline
            class="ml-2"
          />
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div class="d-flex ga-3 align-start">
            <v-text-field
              v-model="section.key"
              label="Section key"
              density="compact"
              variant="outlined"
              hint="The evidence object this section reads"
              :error-messages="diag(`${MODEL_PATH}.sections[${i}].key`)"
            />
            <v-text-field
              :model-value="section.cap ?? ''"
              label="Section cap"
              type="number"
              density="compact"
              variant="outlined"
              :error-messages="diag(`${MODEL_PATH}.sections[${i}].cap`)"
              @update:model-value="v => setNumber(section, 'cap', v)"
            />
            <v-btn
              aria-label="Remove section"
              icon="mdi-delete"
              variant="text"
              color="error"
              @click="model.sections.splice(i, 1)"
            />
          </div>

          <v-card
            v-for="(category, j) in section.categories"
            :key="j"
            variant="outlined"
            class="mb-3"
          >
            <v-card-text>
              <div class="d-flex ga-3 align-start">
                <v-text-field
                  v-model="category.key"
                  label="Category key"
                  density="compact"
                  variant="outlined"
                  :error-messages="diag(`${cat(i, j)}.key`)"
                />
                <v-text-field
                  :model-value="category.cap ?? ''"
                  label="Category cap"
                  type="number"
                  density="compact"
                  variant="outlined"
                  :error-messages="diag(`${cat(i, j)}.cap`)"
                  @update:model-value="v => setNumber(category, 'cap', v)"
                />
                <v-select
                  :model-value="category.combine ?? 'sum'"
                  :items="COMBINE"
                  label="Combine types"
                  density="compact"
                  variant="outlined"
                  :error-messages="diag(`${cat(i, j)}.combine`)"
                  @update:model-value="v => setCombine(category, v)"
                />
                <v-btn
                  aria-label="Remove category"
                  icon="mdi-delete"
                  variant="text"
                  color="error"
                  @click="section.categories.splice(j, 1)"
                />
              </div>
              <PointModelTypes v-model="category.types" :base="`${cat(i, j)}.types`" :diag="diag" />
            </v-card-text>
          </v-card>
          <v-btn
            size="small"
            variant="tonal"
            prepend-icon="mdi-plus"
            @click="section.categories.push({ key: '', types: [] })"
          >
            Category
          </v-btn>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
    <v-btn class="mt-3" variant="tonal" prepend-icon="mdi-plus" @click="addSection">Section</v-btn>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import PointModelTypes from './PointModelTypes.vue'
  import { MODEL_PATH, setNumber, type Category, type DiagFn, type PointModel } from './pointModel'

  defineProps<{ diag: DiagFn; count: (...prefixes: string[]) => number }>()
  const model = defineModel<PointModel>({ required: true })
  const openSections = ref<number[]>([])

  const COMBINE = [
    { title: 'Sum of types', value: 'sum' },
    { title: 'Best type only', value: 'max' }
  ]

  const cat = (i: number, j: number) => `${MODEL_PATH}.sections[${i}].categories[${j}]`

  const setCombine = (category: Category, value: unknown) => {
    if (value === 'max') category.combine = 'max'
    else delete category.combine // sum is the default; keep stored models unchanged
  }

  const addSection = () => {
    model.value.sections.push({ key: '', categories: [] })
    openSections.value = [...openSections.value, model.value.sections.length - 1]
  }
</script>

<style scoped>
  .total-cap {
    max-width: 220px;
  }
</style>
