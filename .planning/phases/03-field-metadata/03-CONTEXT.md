# Phase 3: Field Metadata - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance DynamicField to display rich metadata from field_definitions: icons, hints, tooltips, and help links. This makes fields self-documenting for curators. Validation and scoring are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Icon Placement
- Icons appear in the prepend slot (Vuetify's prepend-inner), inside the field before input
- Styling: subtle muted gray color, same size as field text — doesn't draw attention
- When no icon defined: show a generic default icon (e.g., mdi-information-outline)
- Icons are interactive: hovering shows the field's tooltip (if tooltip property defined)

### Hint Behavior
- Long hints: truncate after ~100 characters with "show more" toggle to expand
- Visual distinction from errors: hints in gray/muted color, errors in red — same position below field
- Display mode (always visible vs on-focus): Claude's discretion based on research
- Formatting support (plain text vs markdown): Claude's discretion based on research

### Tooltip Presentation
- Trigger: hover only — appears on mouse hover, disappears on mouse leave
- Position: auto-detect based on available space (Vuetify default behavior)
- Delay: short delay (~200-300ms) before appearing to prevent accidental triggers
- Content format (text only vs rich): Claude's discretion based on research

### Help Link Design
- Position: append slot, at the end of the field inside the input area
- Icon: question mark circle (mdi-help-circle-outline)
- No tooltip preview on the help icon — just clickable
- Opening behavior (new tab vs modal): Claude's discretion based on research

### Claude's Discretion
- Hint display mode (persistent vs on-focus) — research best practices
- Hint formatting support — research what schema hints typically contain
- Tooltip content format — research best practices
- Help link opening behavior — research UX best practices via web search
- Exact delay timing for tooltips within 200-300ms range
- Handling edge cases (very long tooltips, multiple metadata types on one field)

</decisions>

<specifics>
## Specific Ideas

- Icons should be subtle, not attention-grabbing — the field content is primary
- Help links connect to external documentation (ClinGen SOP, etc.) — curators need quick access
- Truncation prevents long hints from overwhelming the form layout

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-field-metadata*
*Context gathered: 2026-01-22*
