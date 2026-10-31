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

import { defineComponent, h, type Component, type PropType } from 'vue'
import { VCheckbox } from 'vuetify/components/VCheckbox'
import { VCombobox } from 'vuetify/components/VCombobox'
import { VIcon } from 'vuetify/components/VIcon'
import { VSelect } from 'vuetify/components/VSelect'
import { VTextField } from 'vuetify/components/VTextField'
import EvidenceTableField from './EvidenceTableField.vue'
import ReadonlyValue from './ReadonlyValue.vue'
import { rulesFor } from './composables/useValidationRules'
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

/** Typed text in a `lazy` cell is committed after this pause in typing (#469). */
export const CELL_COMMIT_MS = 400

/** Compact editor for an evidence-table cell; `lazy` cells commit on change (blur/Enter) or after a pause in typing, not per keystroke */
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

/** An http(s) URL with a host, else none: never a javascript: or data: link (#538) */
export function safeHref(value: unknown): string | undefined {
  try {
    const url = new URL(String(value ?? '').trim())
    return ['http:', 'https:'].includes(url.protocol) && url.hostname ? url.href : undefined
  } catch {
    return undefined
  }
}

export const urlRule = (value: unknown) => !value || !!safeHref(value) || 'Enter an http(s) URL'

/** Opens a safe URL in a new tab; nothing for anything else */
export function urlLink(value: unknown) {
  const href = safeHref(value)
  return href
    ? h(
        'a',
        {
          href,
          target: '_blank',
          rel: 'noopener noreferrer',
          title: href,
          'aria-label': 'Open link'
        },
        [h(VIcon, { icon: 'mdi-open-in-new', size: 'small' })]
      )
    : null
}

/** `url` field: a text input with an open-link button; read-only it is a link */
const UrlField = defineComponent({
  props: {
    fieldSchema: { type: Object as PropType<FieldSchema>, required: true },
    label: { type: String, default: '' },
    modelValue: { type: null, default: undefined },
    disabled: Boolean,
    readonly: Boolean,
    errorMessages: { type: Array as PropType<string[]>, default: () => [] }
  },
  emits: ['update:model-value'],
  setup(props, { emit }) {
    return () =>
      props.readonly
        ? h(ReadonlyValue, {
            schema: props.fieldSchema,
            modelValue: props.modelValue,
            label: props.label
          })
        : h(
            VTextField,
            {
              type: 'url',
              modelValue: props.modelValue as string | undefined,
              label: props.label,
              hint: props.fieldSchema.hint || props.fieldSchema.description,
              disabled: props.disabled,
              errorMessages: props.errorMessages,
              rules: [...rulesFor(props.fieldSchema), urlRule],
              'onUpdate:modelValue': (v: unknown) => emit('update:model-value', v)
            },
            { 'append-inner': () => urlLink(props.modelValue) }
          )
  }
})

const textCell: CellDef = { is: VTextField, lazy: true }
const numberCell: CellDef = { is: VTextField, props: { type: 'number' }, lazy: true }

export const fieldTypes: Record<string, FieldTypeDef> = {
  string: { cell: textCell, empty: () => '' },
  number: { cell: numberCell, empty: () => null },
  integer: { cell: numberCell, empty: () => null },
  boolean: { cell: { is: VCheckbox }, empty: () => false },
  object: { empty: () => ({}) },
  array: { empty: () => [] },
  multiselect: { empty: () => [] },
  url: {
    editor: UrlField,
    cell: { is: VTextField, props: { type: 'url' }, lazy: true },
    empty: () => ''
  },
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

/** multiselect and array cells hold a list (#577) */
export const isListType = (field: FieldSchema) =>
  field.type === 'multiselect' || field.type === 'array'

export function cellFor(field: FieldSchema): CellDef {
  // Options pick from a list; an array without options takes typed entries
  const list = isListType(field) ? { multiple: true, chips: true, closableChips: true } : {}
  if (field.enum) {
    const items = (field.enumOptions ?? field.enum).map(o =>
      typeof o === 'object' ? { title: o.label ?? o.value, value: o.value } : { title: o, value: o }
    )
    return { is: VSelect, props: { ...list, items } }
  }
  // ponytail: an entry cannot hold a comma or semicolon; fine for PMIDs and source names
  if (isListType(field)) return { is: VCombobox, props: { ...list, delimiters: [',', ';'] } }
  if (field.format === 'date') return { is: VTextField, props: { type: 'date' }, lazy: true }
  return fieldTypes[field.type ?? '']?.cell ?? textCell
}
