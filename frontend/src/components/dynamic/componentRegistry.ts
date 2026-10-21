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

import type { Component } from 'vue'
import { VCheckbox } from 'vuetify/components/VCheckbox'
import { VSelect } from 'vuetify/components/VSelect'
import { VTextField } from 'vuetify/components/VTextField'
import EvidenceTableField from './EvidenceTableField.vue'
import type { FieldSchema } from './types'
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
 */
export const componentRegistry: Record<string, Component> = {
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
export function getComponent(name: string | null | undefined): Component | null {
  if (!name) return null
  return componentRegistry[name] || null
}

/** Compact editor for an evidence-table cell; `lazy` cells commit on change (blur/Enter), not per keystroke */
export interface CellDef {
  is: Component
  props?: Record<string, unknown>
  lazy?: boolean
}

/**
 * Field-type registry: type -> editor, compact cell, empty value.
 * Types without `editor` use the inputs DynamicField renders itself.
 */
export interface FieldTypeDef {
  editor?: Component
  cell?: CellDef
  empty: () => unknown
}

const textCell: CellDef = { is: VTextField, lazy: true }
const numberCell: CellDef = { is: VTextField, props: { type: 'number' }, lazy: true }

export const fieldTypes: Record<string, FieldTypeDef> = {
  string: { cell: textCell, empty: () => '' },
  number: { cell: numberCell, empty: () => null },
  integer: { cell: numberCell, empty: () => null },
  boolean: { cell: { is: VCheckbox }, empty: () => false },
  object: { empty: () => ({}) },
  array: { empty: () => [] },
  evidence_table: {
    // Getter: EvidenceTableField imports this module back, so resolve it at render time
    get editor() {
      return EvidenceTableField
    },
    empty: () => []
  }
}

export function emptyValue(field: FieldSchema): unknown {
  return field.default ?? fieldTypes[field.type ?? '']?.empty() ?? null
}

export function cellFor(field: FieldSchema): CellDef {
  if (field.enum) {
    const items = (field.enumOptions ?? field.enum).map(o =>
      typeof o === 'object' ? { title: o.label ?? o.value, value: o.value } : { title: o, value: o }
    )
    return { is: VSelect, props: { items } }
  }
  if (field.format === 'date') return { is: VTextField, props: { type: 'date' }, lazy: true }
  return fieldTypes[field.type ?? '']?.cell ?? textCell
}
