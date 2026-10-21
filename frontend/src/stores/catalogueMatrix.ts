/**
 * Catalogue matrix store: which scopes are columns, and the server page of genes x scopes.
 * The user's default scope selection lives in localStorage; every access is guarded because
 * storage can be blocked or hold junk, and the page must work without it.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { catalogueMatrixAPI } from '@/api/catalogueMatrix'
import { logService } from '@/services/logService'
import { errorMessage } from './apiError'
import type { Schema } from '@/types/api'

const STORAGE_KEY = 'catalogue.shownScopes'
/** Columns shown when the user has not chosen any (the endpoint accepts up to 50). */
const DEFAULT_COLUMNS = 5

function readSaved(): string[] | null {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string') : null
  } catch {
    return null
  }
}

export interface MatrixFetch {
  scopeIds: string[]
  search?: string
  agreement?: 'agree' | 'disagree'
  page: number
  size: number
  desc?: boolean
}

export const useCatalogueMatrixStore = defineStore('catalogueMatrix', () => {
  const availableScopes = ref<Schema<'ScopeFilterOption'>[]>([])
  /** Scopes the signed-in user belongs to; private or in-progress-only ones are not in the public list. */
  const memberScopes = ref<{ id: string; display_name: string }[]>([])
  const saved = ref<string[] | null>(readSaved())
  const scopes = ref<Schema<'MatrixScope'>[]>([])
  const rows = ref<Schema<'MatrixRow'>[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const allScopes = computed(() => {
    const byId = new Map<string, { id: string; display_name: string }>()
    for (const s of [...availableScopes.value, ...memberScopes.value]) {
      if (!byId.has(s.id)) byId.set(s.id, { id: s.id, display_name: s.display_name })
    }
    return [...byId.values()]
  })

  function setMemberScopes(list: { id: string; display_name: string }[]) {
    memberScopes.value = list
  }

  const defaultShownIds = computed(() => {
    const ids = allScopes.value.map(s => s.id)
    const keep = saved.value?.filter(id => ids.includes(id))
    return keep?.length ? keep : ids.slice(0, DEFAULT_COLUMNS)
  })

  async function loadScopes() {
    try {
      availableScopes.value = await catalogueMatrixAPI.getScopes()
    } catch (err) {
      error.value = errorMessage(err, 'Could not load scopes')
      logService.error('Failed to load catalogue scopes', { error: error.value })
    }
  }

  function saveDefault(ids: string[]) {
    saved.value = ids
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
    } catch {
      // Blocked storage: the choice still applies for this session.
    }
  }

  // Only the latest request may write state; an older, slower response is dropped.
  let latest = 0
  async function fetch(q: MatrixFetch) {
    const mine = ++latest
    error.value = null
    if (!q.scopeIds.length) {
      scopes.value = rows.value = []
      total.value = 0
      return
    }
    loading.value = true
    try {
      const data = await catalogueMatrixAPI.getMatrix({
        scope_ids: q.scopeIds,
        search: q.search || undefined,
        agreement: q.agreement,
        skip: (q.page - 1) * q.size,
        limit: q.size,
        sort_order: q.desc ? 'desc' : 'asc'
      })
      if (mine !== latest) return
      scopes.value = data.scopes
      rows.value = data.rows
      total.value = data.total
    } catch (err) {
      if (mine !== latest) return
      scopes.value = rows.value = []
      total.value = 0
      error.value = errorMessage(err, 'Could not load the catalogue')
      logService.error('Failed to load catalogue matrix', { error: error.value })
    } finally {
      if (mine === latest) loading.value = false
    }
  }

  return {
    availableScopes,
    allScopes,
    setMemberScopes,
    scopes,
    rows,
    total,
    loading,
    error,
    defaultShownIds,
    loadScopes,
    saveDefault,
    fetch
  }
})
