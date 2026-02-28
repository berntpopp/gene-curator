/**
 * Apply workflow pair data mapping to prefill curation data from precuration data.
 *
 * Mirrors the backend logic in backend/app/crud/precuration.py:_prefill_curation_data().
 * Handles nested dot-notation target paths (e.g., "entity_definition.mondo_id").
 *
 * @param {Object|null|undefined} precurationData - Source precuration evidence data
 * @param {Object|null|undefined} dataMapping - Workflow pair data_mapping config
 * @returns {Object} Mapped curation data ready for form initialization
 */
export function applyDataMapping(precurationData, dataMapping) {
  if (!precurationData || !dataMapping) return {}

  const mapping = dataMapping.precuration_to_curation
  if (!mapping || typeof mapping !== 'object') return {}

  const curationData = {}

  for (const [sourceField, targetPath] of Object.entries(mapping)) {
    if (!(sourceField in precurationData)) continue

    const parts = targetPath.split('.')
    let current = curationData

    for (let i = 0; i < parts.length - 1; i++) {
      if (!(parts[i] in current)) {
        current[parts[i]] = {}
      }
      current = current[parts[i]]
    }

    current[parts[parts.length - 1]] = precurationData[sourceField]
  }

  return curationData
}
