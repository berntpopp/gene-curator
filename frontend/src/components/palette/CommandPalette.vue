<template>
  <v-dialog
    :model-value="search.isOpen"
    max-width="620"
    location="top"
    content-class="palette-dialog"
    aria-label="Command palette"
    @update:model-value="v => !v && search.close()"
  >
    <div class="palette" @keydown="onKeydown">
      <div class="palette__bar">
        <v-icon icon="mdi-magnify" size="small" aria-hidden="true" />
        <input
          ref="field"
          :value="search.query"
          class="palette__input"
          role="combobox"
          aria-label="Search genes, curations and scopes, or run a command"
          aria-autocomplete="list"
          :aria-expanded="true"
          :aria-controls="LISTBOX_ID"
          :aria-activedescendant="activeId"
          placeholder="Search genes, curations, scopes"
          autocomplete="off"
          spellcheck="false"
          @input="search.setQuery(($event.target as HTMLInputElement).value)"
        />
        <kbd class="palette__key">Esc</kbd>
      </div>

      <p v-if="search.error" role="alert" class="palette__note palette__note--error">
        {{ search.error }}
      </p>

      <ul v-if="search.showHelp" class="palette__help" aria-label="Keyboard shortcuts">
        <li v-for="s in SHORTCUTS" :key="s.label">
          <span>{{ s.label }}</span>
          <span>
            <kbd v-for="k in s.keys" :key="k" class="palette__key">{{ k }}</kbd>
          </span>
        </li>
      </ul>

      <div v-else :id="LISTBOX_ID" role="listbox" aria-label="Results" class="palette__list">
        <div v-for="group in groups" :key="group.label" role="group" :aria-label="group.label">
          <div class="palette__heading" aria-hidden="true">{{ group.label }}</div>
          <div
            v-for="item in group.items"
            :id="optionId(item.index)"
            :key="item.key"
            role="option"
            :aria-selected="item.index === active"
            class="palette__option"
            :class="{ 'palette__option--active': item.index === active }"
            @mousemove="active = item.index"
            @click="activate(item)"
          >
            <span class="palette__title" :class="{ mono: item.mono }">{{ item.title }}</span>
            <span class="palette__sub">
              <v-chip
                v-if="item.status"
                size="x-small"
                variant="tonal"
                :color="curationStatusColor(item.status)"
                class="mr-2"
              >
                {{ curationStatusLabel(item.status) }}
              </v-chip>
              {{ item.subtitle }}
            </span>
          </div>
        </div>
        <p v-if="empty" class="palette__note">No results for "{{ search.query.trim() }}"</p>
        <p v-else-if="search.loading" class="palette__note">Searching</p>
      </div>

      <div class="palette__foot" aria-hidden="true">
        <span><kbd class="palette__key">↑</kbd><kbd class="palette__key">↓</kbd> move</span>
        <span><kbd class="palette__key">Enter</kbd> open</span>
        <span><kbd class="palette__key">?</kbd> all shortcuts</span>
      </div>
    </div>
  </v-dialog>
</template>

<script setup lang="ts">
  /**
   * Command palette: Ctrl/Cmd+K or "/" opens it; results come from GET /search plus the
   * navigation entries in route meta (the same source and role gating as the side rail).
   * Mounted once in App.vue; other components open it with useSearchStore().open().
   */
  import { computed, nextTick, ref, watch } from 'vue'
  import { useRouter, type RouteLocationRaw } from 'vue-router'
  import { useSearchStore } from '@/stores/search'
  import { SHORTCUTS, useShortcuts } from '@/composables/useShortcuts'
  import { useNavEntries } from '@/components/navigation/useNavEntries'
  import { curationStatusColor, curationStatusLabel } from '@/config/status'

  interface Item {
    key: string
    index: number
    title: string
    subtitle: string
    mono?: boolean
    status?: string
    to: RouteLocationRaw
  }
  const LISTBOX_ID = 'palette-listbox'
  const optionId = (i: number) => `palette-option-${i}`

  const router = useRouter()
  const search = useSearchStore()
  useShortcuts()

  const field = ref<HTMLInputElement | null>(null)
  const active = ref(0)
  let returnTo: HTMLElement | null = null

  const { primary, admin } = useNavEntries()
  const commands = computed(() => {
    const text = search.query.trim().toLowerCase()
    return [...primary.value, ...admin.value].filter(e => e.label.toLowerCase().includes(text))
  })

  const groups = computed(() => {
    let index = 0
    const r = search.results
    const out: { label: string; items: Item[] }[] = []
    const add = (label: string, rows: Omit<Item, 'index'>[]) => {
      if (rows.length) out.push({ label, items: rows.map(row => ({ ...row, index: index++ })) })
    }
    add(
      'Genes',
      (r?.genes ?? []).map(g => ({
        key: `g-${g.id}`,
        title: g.symbol,
        subtitle: g.hgnc_id,
        mono: true,
        to: { name: 'GeneDetail', params: { id: g.id } }
      }))
    )
    add(
      'Curations',
      (r?.curations ?? []).map(c => ({
        key: `c-${c.id}`,
        title: `${c.gene_symbol} curation`,
        subtitle: c.scope_name,
        status: c.status,
        to: { name: 'curation-detail', params: { scopeId: c.scope_id, curationId: c.id } }
      }))
    )
    add(
      'Scopes',
      (r?.scopes ?? []).map(s => ({
        key: `s-${s.id}`,
        title: s.display_name,
        subtitle: s.name,
        to: { name: 'scope-dashboard', params: { scopeId: s.id } }
      }))
    )
    add(
      'Go to',
      commands.value.map(c => ({
        key: `n-${String(c.name)}`,
        title: c.label,
        subtitle: '',
        to: c.to
      }))
    )
    return out
  })

  const flat = computed(() => groups.value.flatMap(g => g.items))
  const empty = computed(
    () => !search.loading && search.query.trim().length >= 2 && flat.value.length === 0
  )
  const activeId = computed(() => (flat.value.length ? optionId(active.value) : undefined))

  watch(flat, () => (active.value = 0))

  function activate(item: Item) {
    search.close()
    void router.push(item.to)
  }

  function onKeydown(e: KeyboardEvent) {
    const n = flat.value.length
    if (e.key === 'Tab') {
      e.preventDefault() // the field is the only tab stop; results use aria-activedescendant
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      if (n) active.value = (active.value + (e.key === 'ArrowDown' ? 1 : -1) + n) % n
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const item = flat.value[active.value]
      if (item) activate(item)
    }
  }

  // Focus the field on open; give focus back to whatever had it on close.
  watch(
    () => search.isOpen,
    async open => {
      if (open) {
        returnTo = document.activeElement as HTMLElement | null
        await nextTick()
        await nextTick()
        field.value?.focus()
      } else {
        returnTo?.focus()
        returnTo = null
      }
    }
  )
</script>

<style>
  .palette-dialog {
    align-self: flex-start;
    margin-top: 12vh;
  }

  .palette {
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgb(var(--v-theme-outline-variant, var(--v-theme-on-surface)));
    border-radius: 8px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
    overflow: hidden;
  }

  .palette__bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .palette__input {
    flex: 1;
    min-width: 0;
    font-size: 15px;
    background: transparent;
    border: 0;
    color: inherit;
    outline: none;
  }

  /* The bar carries the focus ring so the field and its icon read as one control. */
  .palette__input:focus,
  .palette__input:focus-visible {
    outline: none;
  }

  .palette__bar:focus-within {
    box-shadow: inset 0 -2px 0 rgb(var(--v-theme-info));
  }

  .palette__list,
  .palette__help {
    max-height: min(50vh, 380px);
    overflow-y: auto;
    padding: 4px 0 8px;
    margin: 0;
    list-style: none;
  }

  .palette__heading {
    padding: 10px 16px 4px;
    font-size: 12px;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .palette__option,
  .palette__help li {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 8px 16px;
    cursor: pointer;
  }

  .palette__help li {
    cursor: default;
  }

  .palette__option--active {
    background: rgba(var(--v-theme-secondary), 0.12);
  }

  .palette__sub {
    font-size: 12px;
    opacity: 0.7;
    text-align: right;
  }

  .palette__title.mono {
    font-weight: 600;
  }

  .palette__note {
    padding: 12px 16px;
    font-size: 13px;
    opacity: 0.8;
  }

  .palette__note--error {
    color: rgb(var(--v-theme-error));
    opacity: 1;
  }

  .palette__foot {
    display: flex;
    gap: 16px;
    padding: 8px 16px;
    font-size: 12px;
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    background: rgba(var(--v-theme-on-surface), 0.04);
  }

  .palette__key {
    display: inline-block;
    margin: 0 2px;
    padding: 0 5px;
    font: 11px var(--font-mono, monospace);
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: 3px;
  }

  @media (max-width: 600px) {
    .palette-dialog {
      margin-top: 8px;
    }

    .palette__foot {
      display: none;
    }
  }
</style>
