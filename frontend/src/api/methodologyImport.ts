import apiClient from './client'
import type { Schema } from '@/types/api'

export type MethodologyImportResult = Schema<'MethodologyImportResult'>

/** Methodology bundle import (#575), platform admin only; a dry run writes nothing. */
export async function importMethodology(
  bundle: Schema<'MethodologyBundle'>,
  dryRun: boolean
): Promise<MethodologyImportResult> {
  const response = await apiClient.post<MethodologyImportResult>(
    '/schemas/methodologies/import',
    bundle,
    { params: { dry_run: dryRun } }
  )
  return response.data
}

export type VersionMoveResult = Schema<'VersionMoveResult'>

/** Move a schema's curations to a later methodology version (#591); a dry run writes nothing. */
export async function moveToVersion(
  schemaId: string,
  dryRun: boolean,
  version?: number
): Promise<VersionMoveResult> {
  const response = await apiClient.post<VersionMoveResult>(
    `/schemas/curation-schemas/${schemaId}/move-to-version`,
    null,
    { params: { dry_run: dryRun, version } }
  )
  return response.data
}
