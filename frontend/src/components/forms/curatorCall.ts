import { classKey } from '@/config/classification'
import type { CuratorCall } from './CuratorClassificationField.vue'

/** The server's submit rule (#533): a class other than the calculated one needs a rationale. */
export function unexplainedOverride(call: CuratorCall, calculated?: string | null): boolean {
  const proposed = classKey(call.curator_classification)
  return (
    !!proposed &&
    proposed !== classKey(calculated) &&
    !call.curator_classification_rationale?.trim()
  )
}
