/**
 * #453: a legacy curation can lack its disease entity with no usable linked precuration to supply
 * it. The form shows the disease read-only, so it cannot fix that; the server's pinned
 * required-content check (validate-transition) finds it, and Submit is blocked with the reason.
 */
import { watch, type WatchSource } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'

const DISEASE: Record<string, string> = {
  disease_name: 'Disease name',
  mondo_id: 'MONDO ID',
  mode_of_inheritance: 'Mode of inheritance'
}

/** Why Submit is blocked by missing disease fields, or null when none are missing. */
export function diseaseGapMessage(missing: string[], linked: boolean): string | null {
  const names = missing
    .filter(p => p.startsWith('entity_definition.') || p in DISEASE)
    .map(p => p.split('.').pop()!)
    .map(k => DISEASE[k] ?? k)
  if (!names.length) return null
  const source = linked
    ? 'the linked precuration does not supply it (incomplete, or not for this gene and scope)'
    : 'there is no linked precuration to supply it'
  return (
    `Disease entity incomplete (${names.join(', ')}): ${source}. It cannot be edited here; ` +
    'ask a scope admin for an authorized correction of this record before submitting.'
  )
}

export function useDiseaseGap(opts: {
  curationId: () => string | undefined
  /** The curation links a precuration (read when the answer arrives). */
  linked: () => boolean
  /** Re-check when this changes (after a save). */
  checkAt: WatchSource
  report: (message: string | null) => void
}) {
  const workflow = useWorkflowStore()
  watch(
    opts.checkAt,
    async () => {
      const id = opts.curationId()
      if (!id) return
      // The server check also refuses the submit; failing to ask it only skips the early hint
      const result = await workflow.validateTransition('curation', id, 'review').catch(() => null)
      if (result) opts.report(diseaseGapMessage(result.missing_fields ?? [], opts.linked()))
    },
    { immediate: true }
  )
}
