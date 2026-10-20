/**
 * Shared typing helpers for the dynamic form specs.
 *
 * Internal state of script-setup components is read through the instance in
 * tests; these helpers give that access a precise type once instead of per file.
 */

import type { Component } from 'vue'
import type { FieldSchema, FormValidationResult, SectionConfig, TabConfig } from '../types'

/** A tab with the given sections */
export function createTab(sections: SectionConfig[]) {
  return { id: 'test-tab', name: 'Test Tab', sections }
}

/** An object schema with the given properties */
export function createSchema(properties: Record<string, FieldSchema>) {
  return { type: 'object', properties }
}

/** Mount options accepted by the spec helpers (stubs only) */
export type MountOptions = { global?: { stubs?: Record<string, Component | boolean> } }

/** Internal state of DynamicForm exposed to tests through the instance */
export interface FormInternals {
  activeTab: string | null
  backendErrors: Record<string, string[]>
  canSubmit: boolean
  clearFieldBackendError: (fieldPath: string) => void
  findFirstInvalidTab: () => string | null
  formData: Record<string, unknown>
  handleBackendValidation: (result: FormValidationResult | undefined) => void
  handleSubmit: () => Promise<void>
  hasChanges: boolean
  nextTab: () => void
  nonFieldErrors: string[]
  prevTab: () => void
  tabValidationErrors: Record<string, boolean>
  validTabs: TabConfig[]
  validationResult: FormValidationResult | undefined
}

export function vmOf(wrapper: { vm: unknown }): FormInternals {
  return wrapper.vm as FormInternals
}

/** Open accordion sections of TabContent */
export function openSectionsOf(wrapper: { vm: unknown }): number[] {
  return (wrapper.vm as unknown as { openSections: number[] }).openSections
}
