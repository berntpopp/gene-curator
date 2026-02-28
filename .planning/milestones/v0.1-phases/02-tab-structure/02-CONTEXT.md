# Phase 2: Tab Structure - Context

**Gathered:** 2026-01-22
**Status:** Ready for planning

<domain>
## Phase Boundary

DynamicForm organizes fields into tabs and sections based on schema ui_configuration. Users navigate between tabs to access different form sections. Forms without ui_configuration render as flat field lists for backward compatibility.

</domain>

<decisions>
## Implementation Decisions

### Tab Navigation Style
- Horizontal tabs at top of form (standard pattern)
- Scrollable with navigation arrows when many tabs
- Lazy render tabs on first visit, keep alive after (preserves scroll/focus state)
- Mobile behavior: **Research best practices** — let researcher investigate optimal mobile tab patterns

### Section Grouping Within Tabs
- Each section renders as a card with subtle elevation
- Section headers display icons when configured in schema
- Section descriptions appear as subtitles under headers
- Collapsibility: **Research best practices** — let researcher investigate when collapsible sections improve UX

### Score Badge Display
- Badge appears after tab label (e.g., "Evidence [3]")
- Live updates as user edits fields in that tab
- Use Vuetify chip/badge component, colored by score
- No badge shown when scoring isn't configured for that tab

### Empty/Loading States
- Skeleton loaders while tab content loads (lazy render)
- Hide tabs entirely if they have no fields
- Hide sections entirely if they have no fields
- Forms without ui_configuration render as flat field list (backward compatible)

### Claude's Discretion
- Exact skeleton loader design
- Badge color scheme for different score ranges
- Spacing and padding within sections
- Tab icon sizing and placement

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard Vuetify patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-tab-structure*
*Context gathered: 2026-01-22*
