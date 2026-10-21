import { reactive } from 'vue'
import { onScopeDispose } from 'vue'
import { publicationsAPI } from '@/api/publications'

export type PmidStatus = 'idle' | 'invalid' | 'loading' | 'found' | 'notfound' | 'error'
export interface PmidResult {
  status: PmidStatus
  title?: string
  citation?: string
}

const DEBOUNCE_MS = 300
const PMID = /^\d{1,9}$/

/** "PMID: 123" and "123" are the same PMID. */
const normalize = (raw: unknown) =>
  String(raw ?? '')
    .trim()
    .replace(/^PMID:?\s*/i, '')

/**
 * Europe PMC lookup (through the publications API) for PMID cells, on blur.
 * Debounced, one request per cell at a time (a new blur aborts the previous one), results
 * kept per PMID so the same PMID is looked up once. An unknown PMID blocks; a failed lookup
 * does not (offline must not stop curation).
 */
export function usePmidLookup() {
  const results = reactive<Record<string, PmidResult>>({})
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
        const pub = item?.publication
        results[pmid] =
          item?.is_valid && pub
            ? {
                status: 'found',
                title: pub.title,
                citation: [
                  pub.authors[0]?.split(' ')[0],
                  pub.authors.length > 1 && 'et al.',
                  pub.year
                ]
                  .filter(Boolean)
                  .join(' ')
              }
            : // The API also answers 200 when Europe PMC times out or errors: only a real
              // "not found" may block; anything else is a failed lookup (retried on the next blur)
              { status: item?.error?.startsWith('Publication not found') ? 'notfound' : 'error' }
      } catch {
        if (!ctrl.signal.aborted) results[pmid] = { status: 'error' }
      }
    }, DEBOUNCE_MS)
  }

  onScopeDispose(() => [...cells.keys()].forEach(cancel))

  return {
    check,
    cancel,
    statusOf: (raw: unknown): PmidStatus => results[normalize(raw)]?.status ?? 'idle',
    resultOf: (raw: unknown): PmidResult | undefined => results[normalize(raw)],
    hasUnknown: (pmids: unknown[]) => pmids.some(p => results[normalize(p)]?.status === 'notfound')
  }
}
