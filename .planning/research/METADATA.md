# METADATA.md — Field UI Metadata Best Practices

## Problem Statement

Dynamic forms need metadata beyond basic type/validation:
- **Icons** to visually identify field purpose
- **Hints** for persistent guidance
- **Tooltips** for detailed hover information
- **Help links** to external documentation

Current `DynamicField.vue` only supports `title`, `description`, `placeholder`.

## Industry Approaches

### 1. UI Schema Separation (JSON Forms, react-jsonschema-form)

**Pattern:** Two separate objects - data schema and UI schema

```json
// Data schema (what)
{
  "proband_count": { "type": "integer", "minimum": 0 }
}

// UI schema (how)
{
  "proband_count": {
    "ui:help": "Count only unrelated probands",
    "ui:placeholder": "Enter count"
  }
}
```

**Pros:** Clean separation of concerns
**Cons:** Must maintain two parallel structures, merge logic needed

### 2. Inline Extensions (VJSF, vue3-schema-forms)

**Pattern:** Vendor-prefixed properties inline with field definition

```json
{
  "proband_count": {
    "type": "integer",
    "x-display": { "icon": "mdi-account" },
    "x-options": { "hint": "Count unrelated probands" }
  }
}
```

**Pros:** Single object, portable JSON Schema
**Cons:** Vendor-specific, harder to validate

### 3. Props Passthrough (vue3-schema-forms)

**Pattern:** Direct Vuetify props in field definition

```json
{
  "proband_count": {
    "type": "integer",
    "props": {
      "prependIcon": "mdi-account-multiple",
      "hint": "Count only unrelated probands",
      "persistentHint": true
    }
  }
}
```

**Pros:** Direct Vuetify mapping, familiar to Vue developers
**Cons:** Tightly coupled to Vuetify

## Recommended Approach for Gene Curator

**Use inline extension pattern** with explicit, documented properties.

### Extended Field Definition Schema

```json
{
  "proband_count": {
    // Core (existing)
    "type": "integer",
    "label": "Proband Count",
    "required": true,
    "min": 0,

    // UI Metadata (new)
    "icon": "mdi-account-multiple",
    "hint": "Count only unrelated probands",
    "tooltip": "Include probands from independent families. De novo variants provide strongest evidence.",
    "helpUrl": "https://clinicalgenome.org/docs/proband-counting",

    // Display options (new)
    "placeholder": "Enter count",
    "appendIcon": null,
    "density": "default"
  }
}
```

### UI Metadata Properties

| Property | Type | Vuetify Binding | Description |
|----------|------|-----------------|-------------|
| `icon` | string | `:prepend-icon` | MDI icon name (e.g., "mdi-dna") |
| `hint` | string | `:hint` | Persistent hint text below field |
| `tooltip` | string | `v-tooltip` | Detailed hover information |
| `helpUrl` | string | Custom | Link icon to external docs |
| `appendIcon` | string | `:append-icon` | Icon at end of field |
| `appendIconAction` | string | `@click:append` | Action when append icon clicked |
| `density` | string | `:density` | "default", "comfortable", "compact" |
| `variant` | string | `:variant` | Override field variant |

### DynamicField Implementation

```vue
<v-text-field
  v-if="fieldSchema.type === 'integer'"
  :model-value="modelValue"
  :label="fieldSchema.label || fieldSchema.title"
  :hint="fieldSchema.hint"
  :persistent-hint="!!fieldSchema.hint"
  :prepend-icon="fieldSchema.icon"
  :append-icon="fieldSchema.appendIcon || (fieldSchema.helpUrl ? 'mdi-help-circle-outline' : null)"
  :placeholder="fieldSchema.placeholder"
  @click:append="handleAppendClick"
>
  <template v-if="fieldSchema.tooltip" #prepend>
    <v-tooltip :text="fieldSchema.tooltip" location="top">
      <template #activator="{ props }">
        <v-icon v-bind="props" :icon="fieldSchema.icon" />
      </template>
    </v-tooltip>
  </template>
</v-text-field>
```

## Database Schema Update

Add to `field_definitions` JSONB:

```sql
-- Example field with full metadata
{
  "genetic_evidence": {
    "proband_count": {
      "type": "integer",
      "label": "Proband Count",
      "icon": "mdi-account-multiple",
      "hint": "Number of unrelated probands with pathogenic variant",
      "tooltip": "Count probands from independent families. Each proband should have the variant confirmed by sequencing. De novo variants in affected probands provide the strongest evidence.",
      "helpUrl": "https://clinicalgenome.org/site/assets/files/2165/gene_curation_sop_v11.pdf#page=15",
      "required": true,
      "min": 0
    }
  }
}
```

## Migration Path

### Phase 1: Extend DynamicField
- Add support for `icon`, `hint`, `tooltip`, `helpUrl`
- Backward compatible - missing properties are ignored

### Phase 2: Update Seed Data (optional)
- Add UI metadata to existing schema definitions
- Start with high-value fields (complex concepts)

### Phase 3: Schema Editor UI (future milestone)
- Admin UI to manage field metadata
- Preview of field rendering with metadata

## Accessibility Considerations

- **Tooltips must be keyboard-accessible** (use `v-tooltip` with focusable activator)
- **Icons need ARIA labels** (screenreader support)
- **Hints are better than tooltips** for essential info (always visible)
- **Help links should open in new tab** with proper ARIA

```vue
<v-icon
  v-if="fieldSchema.helpUrl"
  icon="mdi-help-circle-outline"
  :aria-label="`Help for ${fieldSchema.label}`"
  @click="openHelp(fieldSchema.helpUrl)"
/>
```

## Sources

- [JSON Forms UI Schema](https://jsonforms.io/docs/uischema/)
- [react-jsonschema-form uiSchema](https://rjsf-team.github.io/react-jsonschema-form/docs/api-reference/uiSchema/)
- [VJSF (Vuetify JSON Schema Form)](https://github.com/koumoul-dev/vuetify-jsonschema-form)
- [vue3-schema-forms](https://github.com/MaciejDybowski/vue3-schema-forms)
- [Vuetify Tooltip Component](https://vuetifyjs.com/en/components/tooltips/)
- [Vue.js Dynamic Forms Best Practices](https://medium.com/@emperorbrains/vue-js-dynamic-forms-best-practices-and-techniques-a633a696283b)
