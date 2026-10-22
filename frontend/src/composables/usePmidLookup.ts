import { inject, provide, reactive, type InjectionKey } from 'vue'
import { onScopeDispose } from 'vue'
import { publicationsAPI } from '@/api/publications'

export type PmidStatus = 'idle' | 'invalid' | 'loading' | 'found' | 'notfound' | 'error'
export interface PmidResult {
  status: PmidStatus
  title?: string
  citation?: string
}

const DEBOUNCE_MS = 300
const BATCH = 10 // at most two waves of five bounded backend lookups
const PMID = /^\d{1,9}$/

/** "PMID: 123" and "123" are the same PMID. */
const normalize = (raw: unknown) =>
  String(raw ?? '')
    .trim()
    .replace(/^PMID:?\s*/i, '')

/** Every PMID under a "pmid" key, at any depth (all evidence tables of a draft), normalized. */
export const pmidsIn = (data: unknown): string[] =>
  Array.isArray(data)
    ? data.flatMap(pmidsIn)
    : data && typeof data === 'object'
      ? Object.entries(data).flatMap(([k, v]) => (k === 'pmid' ? [normalize(v)] : pmidsIn(v)))
      : []

// The curation form and its tables share results, so a PMID is looked up once per form
const RESULTS: InjectionKey<Record<string, PmidResult>> = Symbol('pmid-results')

type Item = Awaited<ReturnType<typeof publicationsAPI.validatePMIDs>>['results'][number]

function toResult(item: Item | undefined): PmidResult {
  const pub = item?.publication
  return item?.is_valid && pub
    ? {
        status: 'found',
        title: pub.title,
        citation: [pub.authors[0]?.split(' ')[0], pub.authors.length > 1 && 'et al.', pub.year]
          .filter(Boolean)
          .join(' ')
      }
    : // The API also answers 200 when Europe PMC times out or errors: only a real
      // "not found" may block; anything else is a failed lookup (retried on the next blur)
      { status: item?.error?.startsWith('Publication not found') ? 'notfound' : 'error' }
}

/**
 * Europe PMC lookup (through the publications API) for PMID cells, on blur.
 * Debounced, one request per cell at a time (a new blur aborts the previous one), results
 * kept per PMID so the same PMID is looked up once. An unknown PMID blocks; a failed lookup
 * does not (offline must not stop curation).
 */
export function usePmidLookup() {
  const outer = inject(RESULTS, null)
  const results = outer ?? reactive<Record<string, PmidResult>>({})
  provide(RESULTS, results)
  const cells = new Map<
    string | number,
    { timer?: ReturnType<typeof setTimeout>; ctrl?: AbortController; pmid?: string }
  >()

  function cancel(cell: string | number) {
    const c = cells.get(cell)
    if (!c) return
    clearTimeout(c.timer)
    c.ctrl?.abort()
    cells.delete(cell)
    // A cancelled lookup must not stay "loading" forever
    if (c.pmid && results[c.pmid]?.status === 'loading') results[c.pmid] = { status: 'idle' }
  }

  function check(cell: string | number, raw: unknown) {
    cancel(cell)
    const pmid = normalize(raw)
    if (!pmid) return
    if (!PMID.test(pmid)) {
      results[pmid] = { status: 'invalid' }
      return
    }
    const known = results[pmid]?.status
    if (known === 'found' || known === 'notfound') return

    results[pmid] = { status: 'loading' }
    const state: { timer?: ReturnType<typeof setTimeout>; ctrl?: AbortController; pmid?: string } =
      {
        pmid
      }
    cells.set(cell, state)
    state.timer = setTimeout(async () => {
      const ctrl = (state.ctrl = new AbortController())
      try {
        const item = (await publicationsAPI.validatePMIDs([pmid], ctrl.signal)).results[0]
        if (ctrl.signal.aborted) return
        results[pmid] = toResult(item)
      } catch {
        if (!ctrl.signal.aborted) results[pmid] = { status: 'error' }
      }
    }, DEBOUNCE_MS)
  }

  /** PMIDs loaded with saved rows: each one never looked up, in sequential batches. */
  const batchCtrl = new AbortController()
  async function checkAll(raws: unknown[]) {
    const pmids = [...new Set(raws.map(normalize))].filter(
      p => PMID.test(p) && ['idle', 'error'].includes(results[p]?.status ?? 'idle')
    )
    for (let i = 0; i < pmids.length; i += BATCH) {
      if (batchCtrl.signal.aborted) return
      const chunk = pmids.slice(i, i + BATCH)
      chunk.forEach(p => (results[p] = { status: 'loading' }))
      try {
        const res = await publicationsAPI.validatePMIDs(chunk, batchCtrl.signal)
        if (batchCtrl.signal.aborted) {
          chunk.forEach(p => {
            if (results[p]?.status === 'loading') results[p] = { status: 'idle' }
          })
          return
        }
        const byPmid = new Map(res.results.map(result => [normalize(result.pmid), result]))
        chunk.forEach(p => (results[p] = toResult(byPmid.get(p))))
      } catch {
        chunk.forEach(p => {
          if (results[p]?.status === 'loading') {
            results[p] = { status: batchCtrl.signal.aborted ? 'idle' : 'error' }
          }
        })
      }
    }
  }

  onScopeDispose(() => {
    ;[...cells.keys()].forEach(cancel)
    batchCtrl.abort()
  })

  return {
    /** Inside a form with its own lookup (the curation form), which owns the submit blocker */
    shared: !!outer,
    check,
    checkAll,
    cancel,
    statusOf: (raw: unknown): PmidStatus => results[normalize(raw)]?.status ?? 'idle',
    resultOf: (raw: unknown): PmidResult | undefined => results[normalize(raw)],
    hasUnknown: (pmids: unknown[]) => pmids.some(p => results[normalize(p)]?.status === 'notfound')
  }
}
