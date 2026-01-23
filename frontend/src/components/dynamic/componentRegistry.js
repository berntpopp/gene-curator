/**
 * Component Registry for Dynamic Field Rendering
 *
 * Maps component names (as specified in curation schema field_definitions)
 * to their Vue component implementations. Used by DynamicField.vue to render
 * specialized input components when specified in the schema.
 *
 * Component names are case-sensitive and must match exactly as used in schemas.
 *
 * @module componentRegistry
 */

import MONDOAutocomplete from '@/components/evidence/MONDOAutocomplete.vue'
import PMIDInput from '@/components/evidence/PMIDInput.vue'
import HPOInheritanceSelect from '@/components/evidence/HPOInheritanceSelect.vue'
import OMIMAutocomplete from '@/components/evidence/OMIMAutocomplete.vue'
import HPOInput from '@/components/evidence/HPOInput.vue'

/**
 * Registry mapping component names to their Vue component implementations.
 *
 * Component purposes:
 * - MONDOAutocomplete: Disease selection using MONDO ontology search
 * - PMIDInput: PubMed ID input with batch validation against Europe PMC
 * - HPOInheritanceSelect: Dropdown for HPO inheritance patterns (AD, AR, XL, etc.)
 * - OMIMAutocomplete: OMIM disease selection with search (single or multiple)
 * - HPOInput: HPO phenotype term input with validation
 *
 * @type {Object.<string, import('vue').Component>}
 */
export const componentRegistry = {
  MONDOAutocomplete,
  PMIDInput,
  HPOInheritanceSelect,
  OMIMAutocomplete,
  HPOInput
}

/**
 * Get a component from the registry by name.
 *
 * @param {string} name - The component name (case-sensitive)
 * @returns {import('vue').Component|null} The component or null if not found
 *
 * @example
 * const component = getComponent('MONDOAutocomplete')
 * if (component) {
 *   // Use the component
 * }
 */
export function getComponent(name) {
  if (!name) return null
  return componentRegistry[name] || null
}
