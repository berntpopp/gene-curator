# Phase 1: Field Rendering - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete DynamicField component to render any field type from schema field_definitions, including nested structures (object, array) and specialized components (MONDOAutocomplete, PMIDInput, HPOInheritanceSelect, OMIMAutocomplete, HPOInput). Users can view and edit all schema-defined fields through dynamically rendered forms.

</domain>

<decisions>
## Implementation Decisions

### Nested field layout
- Keep bordered cards (v-card variant="outlined") for nested objects — follows best practices
- Always expanded, no collapsibility — essential form fields should remain visible
- Label above card (v-label with field title) — current approach is UX-aligned
- Subtle background tint for deeper nesting (level 2+) — shows visual hierarchy through progressive shading

### Array field controls
- No reordering — items stay in order added, simpler UX
- Empty state: placeholder message ("No items added yet") with add button below
- Show "Item 1, Item 2..." numbering — helps users reference specific items
- No delete confirmation — immediate delete for faster workflow

### Field type mapping
- Unknown types: fall back to editable text field (not readonly)
- Warning display: append "(Unknown Type)" to field label
- Format hints: validate format (email → email regex, etc.)
- Supported formats: date only gets specialized input, other formats use text + validation

### Component registry design
- Schema specifies component via explicit `component` property (e.g., `component: 'MONDOAutocomplete'`)
- Registry in separate file (componentRegistry.js) — more maintainable, clear contract
- Eager loading for all 5 specialized components — they're form-critical, not conditional
- Missing component: fall back to text field with warning log
- Props: full schema passthrough — component extracts what it needs

### Claude's Discretion
- Exact background tint colors for nesting depth
- Registry file structure and export pattern
- Warning log format for missing/unknown components
- Format validation regex patterns

</decisions>

<specifics>
## Specific Ideas

- UX research strongly recommends "spacing first, containers when needed" — current bordered card approach is validated
- Nested accordions/collapsibility discouraged for essential form content per NN/Group research
- Component registry pattern follows Vue best practices (patterns.dev, Vue School)
- Lazy loading not worth complexity for 5 small autocomplete components

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-field-rendering*
*Context gathered: 2026-01-22*
