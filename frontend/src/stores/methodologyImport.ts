/**
 * Methodology file import (#282): a dry run shows the plan, confirm writes the same bundle.
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  importMethodology,
  moveToVersion,
  type MethodologyImportResult,
  type VersionMoveResult
} from '@/api/methodologyImport'
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

  /** Move to version (#591): the dry-run plan of one schema, then the same move applied. */
  const movePlan = ref<VersionMoveResult | null>(null)
  const moving = ref(false)

  const move = async (schemaId: string, dryRun: boolean): Promise<VersionMoveResult> => {
    moving.value = true
    try {
      // apply sends the planned version: a 409 means a newer one was published since
      const result = await moveToVersion(schemaId, dryRun, movePlan.value?.to_version)
      movePlan.value = result
      return result
    } finally {
      moving.value = false
    }
  }

  /** Plan a move to the latest version; nothing is written. */
  const planMove = (schemaId: string) => {
    movePlan.value = null
    return move(schemaId, true)
  }

  /** Apply the planned move (same target version as the plan). */
  const applyMove = (schemaId: string) => move(schemaId, false)

  return { plan, importing, dryRun, confirm, movePlan, moving, planMove, applyMove }
})
