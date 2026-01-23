# Phase 5: Scoring and Integration - Context

**Gathered:** 2026-01-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Display live scores based on schema scoring engines (ClinGen, GenCC, Qualitative) and integrate DynamicForm into all form views, replacing hardcoded ClinGen components. This includes:
- Score preview with real-time updates during editing
- Classification labels derived from scoring thresholds
- ClinGen bypass removal from SchemaDrivenCurationForm
- PrecurationFormView refactor to use DynamicForm
- Form recovery (localStorage auto-save) working with DynamicForm

</domain>

<decisions>
## Implementation Decisions

### Score Display
- **Location**: Sticky sidebar panel (always visible on right side during editing)
- **Animation**: Subtle 300ms transitions for score value and color changes
- **Default visibility**: Summary only (total score + classification + category subtotals), with expandable breakdown
- **Loading state**: Skeleton loader placeholders matching the score layout during calculation

### Classification UX
- **Presentation**: Prominent colored chip with icon (green=Definitive, blue=Strong, orange=Moderate, grey=Limited/None)
- **Thresholds**: Expandable reference panel with "View thresholds" button, collapsed by default
- **Color consistency**: Semantic colors across all scoring engines (green=strong evidence, blue=moderate, orange=limited, grey=none)
- **Near-threshold indicator**: Subtle "near threshold" note when within 1 point of next classification

### Bypass Removal Strategy
- **Approach**: Feature flag transition - add schema-level flag to enable DynamicForm, test with one schema first, then flip for all
- **Migration**: Auto-migration on load - evidence_data structure normalized to match new field paths transparently
- **Fallback**: Graceful fallback with warning for unsupported field types (render as text input, console warning)
- **Plan structure**: Single focused plan for bypass removal + migration logic together

### Form Recovery Behavior
- **Auto-save frequency**: 5 seconds (current useFormRecovery default)
- **Recovery prompt**: Modal dialog (current FormRecoveryDialog pattern)
- **Conflict handling**: Prefer localStorage with warning, show option to load server version if newer
- **Expiration**: 24 hours (current default)

### Claude's Discretion
- Exact skeleton loader animation and dimensions
- Score recalculation debounce timing (likely 300-500ms)
- Migration edge cases for malformed evidence_data
- Internal caching strategy for scoring engine results

</decisions>

<specifics>
## Specific Ideas

- Current detail view (CurationDetailView) already has good score display with hero banner - use this as reference for sidebar
- Existing ScorePreview and ScoreSummary components have solid patterns (circular score, category breakdown, threshold reference)
- The useScoring composable handles real-time calculation - extend for multi-engine support
- SchemaDrivenCurationForm already has sticky sidebar pattern at lines 61-65 - build on this

### Research Sources
- [MeasuringU UX Scorecards](https://measuringu.com/ux-scorecard/) - visual hierarchy principles
- [Eleken Healthcare UI](https://www.eleken.co/blog-posts/user-interface-design-for-healthcare-applications) - color coding
- [WebStacks Healthcare UX](https://www.webstacks.com/blog/healthcare-ux-design) - progressive disclosure
- [Design Studio Form UX](https://www.designstudiouiux.com/blog/form-ux-design-best-practices/) - loading states

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 05-scoring-and-integration*
*Context gathered: 2026-01-23*
