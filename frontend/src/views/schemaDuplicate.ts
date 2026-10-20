import type { Schema } from '@/types/api'

/** The API has no duplicate endpoint: a copy is created from the source schema's definition. */
export const toDuplicatePayload = (
  src: Schema<'CurationSchema'>
): Schema<'CurationSchemaCreate'> => ({
  name: `${src.name} (copy)`,
  version: src.version,
  schema_type: src.schema_type,
  institution: src.institution,
  description: src.description,
  field_definitions: src.field_definitions,
  validation_rules: src.validation_rules,
  workflow_states: src.workflow_states,
  ui_configuration: src.ui_configuration,
  scoring_configuration: src.scoring_configuration,
  is_active: false,
  use_dynamic_form: src.use_dynamic_form
})
