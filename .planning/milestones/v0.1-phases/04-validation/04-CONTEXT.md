# Phase 4: Validation - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

DynamicForm enforces schema validation rules with inline error display. This includes client-side validation (required, min/max, patterns, enums) based on field_definitions, plus integration with backend validation errors. Scoring and live calculation are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Error display timing
- Validate on blur (when user leaves the field)
- Errors clear immediately when input becomes valid (reactive)
- Required fields show asterisk (*) on label before interaction
- Array field items validate on blur, same as regular fields

### Error message content
- Use schema-defined errorMessage from field_definitions when present
- Generate concise messages from rules when schema doesn't define one (e.g., "Required" / "Min 3 characters" / "Invalid format")
- No error summary banner — inline errors only
- Show first error only when field has multiple validation failures

### Backend error handling
- Map backend errors to fields inline (same display as client errors)
- Client errors take priority when both exist for same field
- Backend errors clear on any field change (user modifies the field)
- Non-field backend errors display as form-level alert at top of form

### Form submission blocking
- Submit button disabled while form has validation errors
- Invalid tabs show red dot/badge on tab header
- Validate all tabs always (not just active/visited)
- Auto-navigate to first tab with error and focus that field on submit attempt

### Claude's Discretion
- Exact validation rule generation logic
- Error message wording for edge cases
- Form-level alert styling
- Focus management implementation details

</decisions>

<specifics>
## Specific Ideas

- Vuetify's native validation patterns (rules prop) should be leveraged
- Error badge on tabs should match the existing score badge styling but in error color
- First-error-focus provides clear guidance without overwhelming user

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-validation*
*Context gathered: 2026-01-22*
