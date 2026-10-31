<template>
  <BaseDialog v-model="open" persistent size="lg" @cancel="close">
    <template #title>
      <span class="text-title-large">Add genes from a list</span>
    </template>

    <template v-if="!rows">
      <v-textarea
        v-model="text"
        label="Gene symbols or HGNC IDs"
        hint="Separate with new lines, commas, tabs or spaces. Previous symbols and aliases are resolved too."
        persistent-hint
        variant="outlined"
        rows="8"
        auto-grow
        data-testid="paste-input"
        :error-messages="tooMany ? `At most ${MAX_SYMBOLS} entries per list` : ''"
      />
      <div class="text-body-small text-medium-emphasis mt-2" data-testid="paste-count">
        {{ symbols.length }} {{ symbols.length === 1 ? 'entry' : 'entries' }}
      </div>
    </template>

    <template v-else>
      <p ref="summaryEl" class="mb-3" role="status" tabindex="-1" data-testid="summary">
        {{ counts.resolved }} resolved, {{ counts.ambiguous }} ambiguous, {{ counts.not_found }} not
        found{{ dupCount ? `, ${dupCount} repeated` : '' }}. {{ picks.length }} selected.
      </p>
      <div class="d-flex flex-wrap ga-3 mb-3">
        <v-select
          v-model="curatorId"
          :items="curators"
          item-value="user_id"
          item-title="displayName"
          label="Assign to curator (optional)"
          clearable
          density="compact"
          variant="outlined"
          hide-details
          class="intake-option"
          data-testid="curator-picker"
        />
        <v-text-field
          v-model="dueDate"
          type="date"
          label="Due date (optional)"
          clearable
          density="compact"
          variant="outlined"
          hide-details
          class="intake-option"
          data-testid="due-date"
        />
      </div>
      <v-table density="compact" class="intake-table">
        <thead>
          <tr>
            <th scope="col"><span class="sr-only">Include</span></th>
            <th scope="col">Entered</th>
            <th scope="col">Result</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(r, i) in rows" :key="r.item.index" :data-testid="`row-${r.item.status}`">
            <td>
              <v-checkbox-btn
                v-model="r.include"
                density="compact"
                :disabled="!r.pick || r.duplicateOf !== null"
                :aria-label="`Include ${r.item.input}`"
              />
            </td>
            <td class="mono">{{ r.item.input }}</td>
            <td>
              <span v-if="r.duplicateOf !== null" class="text-medium-emphasis">
                Repeats {{ r.duplicateOf }}
              </span>
              <template v-else-if="r.item.status === 'resolved' && r.pick">
                <span class="mono">{{ r.pick.symbol }}</span>
                <span class="text-body-small text-medium-emphasis">
                  {{ r.pick.hgnc_id }} · {{ matchText(r.item.match_type) }}
                </span>
              </template>
              <v-select
                v-else-if="r.item.status === 'ambiguous'"
                :model-value="r.pick?.hgnc_id"
                :items="r.item.candidates ?? []"
                item-value="hgnc_id"
                :item-title="c => `${c.symbol} (${c.hgnc_id})${c.name ? ' · ' + c.name : ''}`"
                label="Choose a gene"
                density="compact"
                variant="outlined"
                hide-details
                :data-testid="`choose-${i}`"
                @update:model-value="choose(r, $event)"
              />
              <span v-else class="text-medium-emphasis" data-testid="not-found">
                {{ reasonText(r.item) }}
              </span>
              <div
                v-if="r.duplicateOf === null && r.pick?.in_scope"
                class="text-body-small text-medium-emphasis"
                data-testid="in-scope"
              >
                {{ inScopeText(r.pick.in_scope_curator) }}
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </template>

    <template #actions>
      <v-btn variant="text" :disabled="busy" @click="close">Cancel</v-btn>
      <v-btn v-if="rows" variant="text" :disabled="busy" @click="rows = null">Edit list</v-btn>
      <v-btn
        v-if="!rows"
        color="primary"
        variant="flat"
        :loading="busy"
        :disabled="!symbols.length || tooMany"
        data-testid="resolve"
        @click="resolve"
      >
        Resolve
      </v-btn>
      <v-btn
        v-else
        color="primary"
        variant="flat"
        :loading="busy"
        :disabled="!picks.length"
        data-testid="add"
        @click="add"
      >
        Add {{ pluralize(picks.length, 'gene') }} to scope
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  /**
   * Paste a list of genes, review how each entry resolved, then add them to the scope and
   * optionally assign them to a curator with a due date in the same step.
   */
  import { computed, nextTick, ref, watch } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { useGeneIntakeStore } from '@/stores/geneIntake'
  import { useScopesStore } from '@/stores/scopes'
  import { toCuratorOption } from '@/components/gene/curatorDisplay'
  import type { CuratorOption } from '@/components/gene/types'
  import { useNotificationsStore } from '@/stores/notifications'
  import { useLogger } from '@/composables/useLogger'
  import { pluralize } from '@/utils/pluralize'
  import type { Schema } from '@/types/api'
  import { readableApiError } from '@/utils/apiErrorText'
  import { MAX_SYMBOLS, parseSymbols, reasonText, toRows, type IntakeRow } from './intake'

  const props = defineProps<{ modelValue: boolean; scopeId: string }>()
  const emit = defineEmits<{ 'update:modelValue': [boolean]; added: [] }>()

  const store = useGeneIntakeStore()
  const scopes = useScopesStore()
  const notifications = useNotificationsStore()
  const logger = useLogger()

  const open = computed({ get: () => props.modelValue, set: v => emit('update:modelValue', v) })
  const text = ref('')
  const rows = ref<IntakeRow[] | null>(null)
  const busy = ref(false)
  const curatorId = ref<string | null>(null)
  const dueDate = ref<string | null>(null)
  const curators = ref<CuratorOption[]>([])
  const summaryEl = ref<HTMLElement | null>(null)
  // A gene the scope already has keeps its curator when added again
  const inScopeText = (curator?: string | null) =>
    curator ? `Already in scope (curator: ${curator}, kept)` : 'Already in scope'

  const symbols = computed(() => parseSymbols(text.value))
  const tooMany = computed(() => symbols.value.length > MAX_SYMBOLS)
  const dupCount = computed(() => rows.value?.filter(r => r.duplicateOf !== null).length ?? 0)
  // From the rows, not the API counts: a repeated entry is counted once, like the Add button (#393)
  const counts = computed(() => {
    const c: Schema<'GeneResolveCounts'> = { resolved: 0, ambiguous: 0, not_found: 0 }
    for (const r of rows.value ?? []) if (r.duplicateOf === null) c[r.item.status]++
    return c
  })
  const picks = computed(() =>
    (rows.value ?? []).flatMap(r => (r.include && r.pick ? [r.pick] : []))
  )

  const MATCH = {
    symbol: 'symbol',
    previous_symbol: 'previous symbol',
    alias: 'alias',
    hgnc_id: 'HGNC ID'
  }
  const matchText = (t?: keyof typeof MATCH | null) => (t ? MATCH[t] : '')

  function choose(row: IntakeRow, hgncId: string) {
    row.pick = row.item.candidates?.find(c => c.hgnc_id === hgncId) ?? null
    row.include = !!row.pick
  }

  function close() {
    open.value = false
  }

  async function resolve() {
    busy.value = true
    try {
      const r = await store.resolve(symbols.value, props.scopeId)
      rows.value = toRows(r.items)
      // Screen readers hear the summary (role=status); keyboard focus moves to it
      await nextTick()
      summaryEl.value?.focus()
    } catch (e) {
      logger.error('Gene resolve failed', { error: (e as Error).message })
      const why = readableApiError(e, '')
      notifications.addToast(
        why && (e as { response?: unknown }).response
          ? `Could not resolve the list. ${why}`
          : 'Could not resolve the list. Try again.',
        'error'
      )
    } finally {
      busy.value = false
    }
  }

  async function add() {
    busy.value = true
    try {
      const r = await store.addToScope(
        props.scopeId,
        picks.value,
        curatorId.value,
        dueDate.value || null
      )
      const total = !r.added && !r.alreadyInScope && r.failed
      const parts = [`${pluralize(r.added, 'gene')} added`]
      if (r.alreadyInScope) parts.push(`${r.alreadyInScope} already in scope`)
      if (r.failed) parts.push(`${r.failed} failed`)
      if (r.notAssigned) parts.push(`${r.notAssigned} not assigned to the curator`)
      const warn = r.failed || r.notAssigned
      notifications.addToast(parts.join(', '), total ? 'error' : warn ? 'warning' : 'success')
      if (!total) {
        emit('added')
        close()
      }
    } catch (e) {
      logger.error('Adding genes to scope failed', { error: (e as Error).message })
      notifications.addToast('Could not add the genes to the scope', 'error')
    } finally {
      busy.value = false
    }
  }

  async function loadCurators() {
    try {
      const members = await scopes.fetchMembers(props.scopeId)
      curators.value = members
        .filter(m => ['curator', 'admin'].includes(m.role))
        .map(toCuratorOption)
    } catch (e) {
      // The picker stays empty; genes can still be added unassigned
      logger.error('Loading curators failed', { error: (e as Error).message })
    }
  }

  // A reopened dialog starts empty
  watch(
    open,
    v => {
      if (v) {
        text.value = ''
        rows.value = null
        curatorId.value = null
        dueDate.value = null
        loadCurators()
      }
    },
    { immediate: true }
  )
</script>

<style scoped>
  .mono {
    font-family: 'IBM Plex Mono', monospace;
    margin-right: 8px;
  }

  .intake-option {
    flex: 1 1 220px;
  }

  .intake-table {
    max-height: 50vh;
    overflow-y: auto;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
