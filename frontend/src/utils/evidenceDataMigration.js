/**
 * Migrate legacy ClinGen evidence_data format to DynamicForm format
 *
 * Legacy format (from ClinGenCurationForm):
 * - evidence_items: Array of evidence item objects
 * - Nested structures specific to ClinGen tabs
 *
 * DynamicForm format:
 * - Flat field structure matching schema field_definitions
 * - _version field to mark migrated data
 */

export function migrateLegacyFormat(evidenceData) {
  // Return unchanged if already migrated
  if (evidenceData?._version === '2.0') {
    return evidenceData
  }

  // Return unchanged if no data
  if (!evidenceData || Object.keys(evidenceData).length === 0) {
    return evidenceData
  }

  // Check if this looks like ClinGen legacy format
  const isLegacyFormat =
    evidenceData.evidence_items !== undefined ||
    evidenceData.disease_entity !== undefined ||
    evidenceData.genetic_evidence !== undefined

  if (!isLegacyFormat) {
    return { ...evidenceData, _version: '2.0' }
  }

  // Migrate ClinGen legacy format
  const migrated = {
    _version: '2.0',

    // Disease entity fields
    disease_name: evidenceData.disease_entity?.name || evidenceData.disease_name || '',
    mondo_id: evidenceData.disease_entity?.mondo_id || evidenceData.mondo_id || '',
    mode_of_inheritance:
      evidenceData.disease_entity?.inheritance || evidenceData.mode_of_inheritance || '',

    // Preserve genetic_evidence and experimental_evidence structures
    genetic_evidence: evidenceData.genetic_evidence || {},
    experimental_evidence: evidenceData.experimental_evidence || {},

    // Preserve other top-level fields
    ...Object.fromEntries(
      Object.entries(evidenceData).filter(([key]) => !['disease_entity', '_version'].includes(key))
    )
  }

  return migrated
}

export function isLegacyFormat(evidenceData) {
  return (
    evidenceData &&
    !evidenceData._version &&
    (evidenceData.evidence_items !== undefined || evidenceData.disease_entity !== undefined)
  )
}
