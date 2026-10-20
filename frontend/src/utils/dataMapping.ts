/**
 * Apply workflow pair data mapping to prefill curation data from precuration data.
 *
 * Mirrors the backend logic in backend/app/crud/precuration.py:_prefill_curation_data().
 * Handles nested dot-notation target paths (e.g., "entity_definition.mondo_id").
 */

export type EvidenceRecord = Record<string, unknown>

export interface DataMappingConfig {
  precuration_to_curation?: Record<string, string> | null
  [key: string]: unknown
}

/**
 * @param precurationData - Source precuration evidence data
 * @param dataMapping - Workflow pair data_mapping config
 * @returns Mapped curation data ready for form initialization
 */
export function applyDataMapping(
  precurationData: EvidenceRecord | null | undefined,
  dataMapping: DataMappingConfig | null | undefined
): EvidenceRecord {
  if (!precurationData || !dataMapping) return {}

  const mapping = dataMapping.precuration_to_curation
  if (!mapping || typeof mapping !== 'object') return {}

  const curationData: EvidenceRecord = {}

  for (const [sourceField, targetPath] of Object.entries(mapping)) {
    if (!(sourceField in precurationData)) continue

    const parts = targetPath.split('.')
    const leaf = parts.pop() ?? ''
    let current: EvidenceRecord = curationData

    for (const part of parts) {
      if (!(part in current)) {
        current[part] = {}
      }
      current = current[part] as EvidenceRecord
    }

    current[leaf] = precurationData[sourceField]
  }

  return curationData
}
