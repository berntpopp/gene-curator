/**
 * Methodology file import (#282): a dry run shows the plan, confirm writes the same bundle.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { importMethodology, type MethodologyImportResult } from '@/api/methodologyImport'
import type { Schema } from '@/types/api'

type Bundle = Schema<'MethodologyBundle'>

export const useMethodologyImportStore = defineStore('methodologyImport', () => {
  const plan = ref<MethodologyImportResult | null>(null)
  const importing = ref(false)
  let bundle: Bundle | null = null

  const run = async (dryRun: boolean) => {
    importing.value = true
    try {
      return await importMethodology(bundle as Bundle, dryRun)
    } finally {
      importing.value = false
    }
  }

  /** Plan the import of `next`; nothing is written. */
  const dryRun = async (next: Bundle): Promise<MethodologyImportResult> => {
    bundle = next
    plan.value = null
    plan.value = await run(true)
    return plan.value
  }

  /** Write the planned bundle. A 422 carries a fresh report, which replaces the plan. */
  const confirm = async (): Promise<MethodologyImportResult> => {
    try {
      return await run(false)
    } catch (error) {
      const report = (error as { response?: { data?: { detail?: MethodologyImportResult } } })
        .response?.data?.detail
      if (Array.isArray(report?.errors)) plan.value = report
      throw error
    }
  }

  return { plan, importing, dryRun, confirm }
})
