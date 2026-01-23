# Phase 5: Scoring and Integration - Research

**Researched:** 2026-01-23
**Domain:** Vue 3 dynamic scoring UI, form integration patterns, schema-based scoring engines
**Confidence:** HIGH

## Summary

Phase 5 integrates live scoring display into DynamicForm and replaces hardcoded ClinGen components with the schema-driven architecture. This research identifies the standard patterns for real-time UI updates, sticky sidebar scoring panels, and progressive component migration strategies.

**Current State:** The codebase already has comprehensive scoring infrastructure:
- Backend: Three scoring engines (ClinGen SOP v11, GenCC, Qualitative) via `backend/app/scoring/registry.py`
- Frontend: `useScoring` composable for client-side preview, `ScorePreview.vue` component with Vuetify 3 patterns
- Validation: Backend returns `score_calculations` in validation response (already implemented in `schema_validator.py`)
- Forms: `DynamicForm.vue` displays basic score cards (lines 134-158), `SchemaDrivenCurationForm.vue` has sticky sidebar pattern (lines 60-65)

**Key Challenge:** The bypass exists because ClinGen has complex custom UI (`ClinGenCurationForm.vue` with tabbed sections, evidence management). Migration requires DynamicForm to handle all ClinGen features while maintaining scoring display for all schema types.

**Primary recommendation:** Build unified ScoreDisplay component that works with any scoring engine, integrate into DynamicForm sidebar, remove isClinGenSchema bypass after DynamicForm feature parity.

## Standard Stack

The established libraries/tools for Vue 3 real-time scoring and form integration:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vue 3 Composition API | 3.4+ | Reactive scoring logic | Native Vue 3 feature, optimal performance for computed/watch patterns |
| Vuetify 3 | 3.5+ | UI components (v-card, v-skeleton-loader, v-chip) | Project standard, Material Design 3 support |
| Pinia | 2.1+ | Validation state management | Project standard for stores |
| VueUse | 10.7+ | watchDebounced, refDebounced utilities | Community standard for Vue composables |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lodash-es | 4.17+ | debounce utility (fallback) | If not using VueUse |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| VueUse watchDebounced | Custom setTimeout-based debounce | VueUse provides battle-tested implementation with cleanup |
| Vuetify skeleton loaders | Custom CSS animations | Vuetify matches design system, built-in Material Design motion |
| Composition API | Options API | Composition API better for complex reactive logic sharing (scoring + validation) |

**Installation:**
```bash
# Already installed in project
cd frontend && npm install # Includes vue, vuetify, pinia, vueuse
```

## Architecture Patterns

### Recommended Scoring Display Structure
```
frontend/src/components/
├── dynamic/
│   ├── DynamicForm.vue         # Main form with scoring integration
│   ├── ScoreDisplay.vue        # NEW: Unified scoring sidebar
│   ├── TabContent.vue          # Existing tab renderer
│   └── DynamicField.vue        # Existing field renderer
├── evidence/
│   └── ScorePreview.vue        # Existing ClinGen-specific preview
└── clingen/
    └── ClinGenCurationForm.vue # To be deprecated after migration
```

### Pattern 1: Real-time Scoring with Debounced Validation
**What:** Trigger backend validation (with scoring) on field changes, debounced to avoid excessive API calls
**When to use:** Any form with live scoring requirements (DynamicForm, all schema types)
**Example:**
```vue
<!-- Source: Existing DynamicForm.vue lines 426-430 + VueUse patterns -->
<script setup>
import { watchDebounced } from '@vueuse/core'
import { useValidationStore } from '@/stores/validation'

const validationStore = useValidationStore()
const formData = ref({})
const validationResult = computed(() => validationStore.getValidationResult('form'))

// Debounced validation on form data changes
watchDebounced(
  formData,
  async (newData) => {
    if (Object.keys(newData).length > 0) {
      await validationStore.validateEvidence(newData, props.schemaId, 'form')
    }
  },
  { debounce: 500, deep: true, maxWait: 2000 }
)
</script>
```

**Key Insight:** Current DynamicForm uses setTimeout-based debounce (lines 386-389, 426-430). VueUse `watchDebounced` provides better cleanup and maxWait option to prevent indefinite delays.

### Pattern 2: Schema-Agnostic Score Display
**What:** Single component that adapts to any scoring engine (ClinGen, GenCC, Qualitative)
**When to use:** DynamicForm sidebar, all schema types
**Example:**
```vue
<!-- Source: Pattern derived from ScoreDisplay.vue + backend scoring registry -->
<template>
  <v-card>
    <v-card-title>
      <v-icon start>mdi-calculator</v-icon>
      Live Scoring
    </v-card-title>
    <v-card-text>
      <!-- Skeleton loader during calculation -->
      <v-skeleton-loader
        v-if="loading"
        type="list-item-avatar@3"
        :boilerplate="false"
      />

      <!-- Score cards by category -->
      <v-row v-else dense>
        <v-col
          v-for="(score, category) in scoreCalculations"
          :key="category"
          cols="12"
        >
          <v-card variant="outlined">
            <v-card-text class="d-flex align-center">
              <div class="flex-grow-1">
                <div class="text-caption text-medium-emphasis">
                  {{ formatCategory(category) }}
                </div>
                <div class="text-h5 font-weight-bold" :class="getScoreColorClass(score)">
                  {{ score.toFixed(2) }}
                </div>
              </div>
              <v-icon :color="getScoreColor(score)" size="large">
                {{ getCategoryIcon(category) }}
              </v-icon>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Classification chip -->
      <v-chip
        v-if="classification"
        :color="getClassificationColor(classification)"
        size="large"
        variant="flat"
        class="mt-4"
        block
      >
        <v-icon start>{{ getClassificationIcon(classification) }}</v-icon>
        {{ classification }}
      </v-chip>

      <!-- Expandable threshold reference -->
      <v-expansion-panels v-if="thresholds" class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-information</v-icon>
            Classification Thresholds
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-list density="compact">
              <v-list-item v-for="(threshold, level) in thresholds" :key="level">
                <template #prepend>
                  <v-chip :color="getClassificationColor(level)" size="small" />
                </template>
                <v-list-item-title>{{ level }}</v-list-item-title>
                <v-list-item-subtitle>≥ {{ threshold }} points</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  scoreCalculations: Object,   // From validationResult.score_calculations
  classification: String,       // From validationResult.classification
  thresholds: Object,          // From schema.scoring_configuration.classification_thresholds
  loading: Boolean
})

// Schema-agnostic formatting
function formatCategory(category) {
  return category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Color mapping (works for ClinGen, GenCC, Qualitative)
function getScoreColor(score) {
  if (score >= 7) return 'success'
  if (score >= 2) return 'warning'
  return 'info'
}
</script>
```

### Pattern 3: Sticky Sidebar with Responsive Behavior
**What:** Sidebar that stays visible during scrolling, collapses on mobile
**When to use:** DynamicForm scoring display (Phase 5), evidence lists
**Example:**
```vue
<!-- Source: Existing SchemaDrivenCurationForm.vue lines 60-65 + Vuetify best practices -->
<template>
  <v-row>
    <v-col cols="12" :lg="showScoring ? 8 : 12">
      <!-- Main form content -->
      <DynamicForm v-bind="formProps" />
    </v-col>

    <v-col v-if="showScoring" cols="12" lg="4">
      <div class="sticky-sidebar">
        <ScoreDisplay v-bind="scoreProps" />
      </div>
    </v-col>
  </v-row>
</template>

<style scoped>
.sticky-sidebar {
  position: sticky;
  top: 80px;  /* Below app bar */
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  transition: all 0.3s ease;  /* Smooth score updates */
}

/* Mobile: non-sticky */
@media (max-width: 1280px) {
  .sticky-sidebar {
    position: static;
    max-height: none;
  }
}
</style>
```

**Key Insight:** Existing pattern at `SchemaDrivenCurationForm.vue:634-640` is solid. Vuetify's `lg` breakpoint (1280px) matches desktop/tablet split.

### Pattern 4: Progressive Migration with Feature Flag
**What:** Gradual replacement of hardcoded components using schema-level flag
**When to use:** Removing ClinGen bypass (INTG-01), testing DynamicForm with one schema before rollout
**Example:**
```javascript
// Source: Research on feature flag patterns + Vue component conditional rendering

// Step 1: Add feature flag to schema (backend migration)
// database/migrations/XXX_add_use_dynamic_form_flag.sql
ALTER TABLE curation_schemas ADD COLUMN use_dynamic_form BOOLEAN DEFAULT false;

// Step 2: Update one test schema
UPDATE curation_schemas SET use_dynamic_form = true WHERE name = 'Test ClinGen Schema';

// Step 3: Conditional rendering in SchemaDrivenCurationForm.vue
const useDynamicForm = computed(() => {
  // Feature flag takes precedence
  if (schema.value?.use_dynamic_form !== undefined) {
    return schema.value.use_dynamic_form
  }
  // Fallback: non-ClinGen schemas always use DynamicForm
  return !isClinGenSchema.value
})

// Step 4: Render appropriate component
<DynamicForm v-if="useDynamicForm" v-bind="dynamicFormProps" />
<ClinGenCurationForm v-else v-bind="clingenFormProps" />

// Step 5: After verification, flip all schemas
UPDATE curation_schemas SET use_dynamic_form = true;

// Step 6: Remove feature flag code + ClinGenCurationForm
```

**Key Insight:** This is safer than immediate replacement. Allows testing with real curations, easy rollback if issues found.

### Anti-Patterns to Avoid
- **Computed properties for debouncing:** Computed properties must be synchronous. Use `watch` or `watchDebounced` instead.
- **Inline scoring calculation:** Keep scoring logic in backend/scoring engines. Frontend only displays results.
- **Direct localStorage for scores:** Scores derived from evidence data, no need to cache separately (form recovery handles evidence data).
- **Hardcoded engine checks:** Use `schema.scoring_configuration.engine` dynamically, don't check `if (engine === 'clingen')`.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debouncing input | Custom setTimeout wrapper | `watchDebounced` from VueUse | Handles cleanup, maxWait, immediate option |
| Skeleton loaders | Custom CSS animations | `v-skeleton-loader` from Vuetify 3 | Matches design system, 30+ built-in types |
| Score color mapping | Switch statements in every component | Centralized `getScoreColor` composable | Single source of truth, consistent across app |
| Form recovery | Manual localStorage save/restore | Existing `useFormRecovery` composable | Already handles dirty checking, expiration, conflict resolution |
| Nested field paths | String splitting logic | Existing `setNestedValue` utility in DynamicForm | Tested, handles edge cases |

**Key insight:** The codebase already solves most problems. Phase 5 is about **integration and unification**, not building new infrastructure.

## Common Pitfalls

### Pitfall 1: Over-Fetching with Validation API
**What goes wrong:** Every field change triggers full validation + scoring, overwhelming backend
**Why it happens:** Form has 20+ fields, user types quickly, no debouncing or request cancellation
**How to avoid:**
- Debounce validation calls (500ms standard, 300ms acceptable for fast feedback)
- Use `maxWait` option (2000ms) to ensure validation eventually runs
- Cancel pending requests when new validation starts (AbortController)
**Warning signs:**
- Network tab shows overlapping validation requests
- Score display lags behind user input
- Backend logs show high validation endpoint load

**Prevention code:**
```javascript
// Source: VueUse watchDebounced + AbortController pattern
import { watchDebounced } from '@vueuse/core'

let abortController = null

watchDebounced(
  formData,
  async (newData) => {
    // Cancel previous request
    if (abortController) {
      abortController.abort()
    }

    abortController = new AbortController()

    try {
      await validationStore.validateEvidence(
        newData,
        schemaId,
        'form',
        { signal: abortController.signal }
      )
    } catch (error) {
      if (error.name !== 'AbortError') {
        logger.error('Validation failed', { error })
      }
    }
  },
  { debounce: 500, maxWait: 2000, deep: true }
)
```

### Pitfall 2: Score Display Flickering During Updates
**What goes wrong:** Score cards flash between values when validation updates, jarring UX
**Why it happens:** Vuetify transitions not configured, immediate DOM updates without animation
**How to avoid:**
- Use CSS transitions on score value changes (300ms duration)
- Keep previous score visible during loading (don't hide immediately)
- Vuetify `v-skeleton-loader` with `boilerplate: false` for smooth loading states
**Warning signs:**
- Numbers visibly jump between values
- Cards flash or resize abruptly
- Users report "flickering" or "jumpy" UI

**Prevention code:**
```vue
<!-- Source: Vuetify 3 transition best practices + Material Design motion -->
<template>
  <div class="score-value-wrapper">
    <transition name="score-fade" mode="out-in">
      <div :key="scoreValue" class="score-value">
        {{ scoreValue.toFixed(2) }}
      </div>
    </transition>
  </div>
</template>

<style scoped>
.score-value {
  transition: color 0.3s ease, transform 0.3s ease;
}

.score-fade-enter-active,
.score-fade-leave-active {
  transition: opacity 0.3s ease;
}

.score-fade-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}

.score-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

/* Prevent layout shift */
.score-value-wrapper {
  min-width: 60px;
  text-align: center;
}
</style>
```

### Pitfall 3: Evidence Data Migration Breaking Existing Curations
**What goes wrong:** Changing evidence_data structure causes existing curations to fail validation/scoring
**Why it happens:** DynamicForm expects different field paths than ClinGenCurationForm used
**How to avoid:**
- Auto-migration on load: Transform old structure to new transparently
- Backend handles both formats during transition period
- Version field in evidence_data to detect old format
**Warning signs:**
- Existing curations show "no data" or validation errors
- Scores don't calculate for old curations
- Users report "my curation is broken"

**Prevention code:**
```javascript
// Source: Pattern from SchemaDrivenCurationForm.vue data loading

async function loadCuration(curationId) {
  const curation = await curationsStore.fetchCurationById(curationId)

  // Auto-migrate old evidence_data format
  if (curation.evidence_data && !curation.evidence_data._version) {
    logger.info('Migrating legacy evidence_data format', { curationId })
    evidenceData.value = migrateLegacyFormat(curation.evidence_data)
  } else {
    evidenceData.value = curation.evidence_data || {}
  }
}

function migrateLegacyFormat(oldData) {
  // Example: ClinGen nested structure to flat DynamicForm structure
  return {
    _version: '2.0',  // Mark as migrated
    disease_name: oldData.disease_entity?.name || '',
    genetic_evidence: oldData.genetic_evidence || {},
    experimental_evidence: oldData.experimental_evidence || {},
    // ... other mappings
  }
}
```

### Pitfall 4: Sticky Sidebar Overlapping Content on Small Laptops
**What goes wrong:** Sticky sidebar covers content on 13" laptops (1440x900) due to fixed positioning
**Why it happens:** `top: 80px` assumes tall viewport, doesn't account for short screens
**How to avoid:**
- Use Vuetify breakpoints: sticky only on `lg` and up (1280px+)
- Test on 1366x768 and 1440x900 (common laptop resolutions)
- Fallback to static positioning below 1280px width
**Warning signs:**
- Sidebar overlaps form on smaller laptops
- Scroll position "jumps" unexpectedly
- Content hidden behind sticky sidebar

**Prevention pattern:** Already implemented correctly in `SchemaDrivenCurationForm.vue:634-640`. Use this as reference.

## Code Examples

Verified patterns from codebase and official sources:

### Real-time Validation with Score Display
```vue
<!-- Source: DynamicForm.vue lines 134-158 + watchDebounced pattern -->
<template>
  <v-card>
    <v-card-text>
      <!-- Form fields -->
      <DynamicField v-for="..." />

      <!-- Live scoring display -->
      <div v-if="validationResult && validationResult.score_calculations">
        <v-divider class="my-6" />
        <h3 class="text-h6 mb-4 d-flex align-center">
          <v-icon start>mdi-calculator</v-icon>
          Live Scoring
        </h3>
        <v-row>
          <v-col
            v-for="(score, category) in validationResult.score_calculations"
            :key="category"
            cols="12"
            sm="6"
            md="4"
          >
            <v-card variant="outlined">
              <v-card-text class="text-center">
                <div class="text-h4 text-primary font-weight-bold">
                  {{ score }}
                </div>
                <div class="text-caption text-uppercase text-medium-emphasis">
                  {{ formatScoreCategory(category) }}
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { watchDebounced } from '@vueuse/core'

// Debounced validation that includes scoring
watchDebounced(
  formData,
  async (newData) => {
    if (Object.keys(newData).length > 0) {
      await validationStore.validateEvidence(newData, props.schemaId, 'form')
    }
  },
  { debounce: 500, maxWait: 2000, deep: true }
)
</script>
```

### Schema-Based Score Calculation (Backend)
```python
# Source: backend/app/core/schema_validator.py lines 843-883
def _calculate_scores(
    self,
    evidence_data: dict[str, Any],
    scoring_config: dict[str, Any],
    result: SchemaValidationResult,
) -> None:
    """Calculate scores based on scoring configuration."""
    engine_type = scoring_config.get("engine", "")

    if engine_type == "clingen":
        self._calculate_clingen_scores(evidence_data, scoring_config, result)
    elif engine_type == "gencc":
        self._calculate_gencc_scores(evidence_data, scoring_config, result)
    elif engine_type == "qualitative":
        self._calculate_qualitative_scores(evidence_data, scoring_config, result)

def _calculate_clingen_scores(
    self,
    evidence_data: dict[str, Any],
    scoring_config: dict[str, Any],
    result: SchemaValidationResult,
) -> None:
    """Calculate ClinGen SOP v11 scores."""
    genetic_evidence = evidence_data.get("genetic_evidence", {})
    experimental_evidence = evidence_data.get("experimental_evidence", {})

    # Calculate genetic evidence score
    genetic_score = (
        genetic_evidence.get("case_level_score", 0)
        + genetic_evidence.get("segregation_score", 0)
        + genetic_evidence.get("case_control_score", 0)
    )

    # Calculate experimental evidence score
    experimental_score = (
        experimental_evidence.get("functional_score", 0)
        + experimental_evidence.get("model_system_score", 0)
        + experimental_evidence.get("rescue_score", 0)
    )

    # Store in result
    result.score_calculations["genetic_evidence_score"] = genetic_score
    result.score_calculations["experimental_evidence_score"] = experimental_score
    result.score_calculations["total_score"] = genetic_score + experimental_score
```

### Skeleton Loader for Score Loading State
```vue
<!-- Source: Vuetify 3 documentation + DynamicForm loading pattern -->
<template>
  <v-card>
    <v-card-title>Live Scoring</v-card-title>
    <v-card-text>
      <!-- Loading state with skeleton -->
      <v-skeleton-loader
        v-if="loading"
        type="list-item-avatar@3"
        :boilerplate="false"
        class="score-skeleton"
      />

      <!-- Actual scores -->
      <v-list v-else>
        <v-list-item v-for="(score, category) in scoreCalculations" :key="category">
          <template #prepend>
            <v-avatar :color="getScoreColor(score)">
              <span class="text-h6">{{ score.toFixed(1) }}</span>
            </v-avatar>
          </template>
          <v-list-item-title>{{ formatCategory(category) }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<style scoped>
/* Match skeleton dimensions to actual content */
.score-skeleton {
  min-height: 200px;
}

/* Smooth transition when loading completes */
.v-list {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Options API with data() | Composition API with ref/reactive | Vue 3 (2020) | Better logic organization for complex forms |
| Manual debounce with setTimeout | VueUse watchDebounced | VueUse 10.0 (2023) | Cleaner code, automatic cleanup |
| Inline skeleton HTML | v-skeleton-loader component | Vuetify 3.0 (2022) | Consistent loading states |
| Hardcoded ClinGen form | Schema-driven DynamicForm | Phase 2 (2025) | Support for multiple methodologies |
| Client-side scoring only | Backend scoring with client preview | Phase 3 (2025) | Authoritative scores, consistent calculation |
| Feature flags in .env | Schema-level flags in database | Current (2026) | Per-schema control, no deployment for changes |

**Deprecated/outdated:**
- **Vue 2 watch with immediate + flush: 'post'**: Vue 3 `watchEffect` or `watchDebounced` is clearer
- **Vuetify 2 v-skeleton-loader API**: Vuetify 3 changed prop names (`boilerplate` instead of `tile`)
- **Global debounce configuration**: Per-watcher debounce allows different delays for different inputs

## Open Questions

Things that couldn't be fully resolved:

1. **Should score recalculation happen on every field change or only on "scoreable" field changes?**
   - What we know: Current implementation validates on any change (lines 426-430 in DynamicForm)
   - What's unclear: Performance impact with 20+ fields, whether scoring engine can short-circuit unchanged categories
   - Recommendation: Keep current behavior (validate on any change) but investigate scoring engine caching in Phase 5.5 if performance issues observed

2. **How to handle score display when multiple tabs have scoring (both genetic and experimental)?**
   - What we know: Tab badges show individual category scores (DynamicForm lines 22-29)
   - What's unclear: Should sidebar show only active tab's score or always show all categories?
   - Recommendation: Show all categories in sidebar (always visible context), use tab badges for quick reference. User testing in Phase 5.2 can validate.

3. **Should classification thresholds be expandable by default or collapsed?**
   - What we know: CONTEXT.md specifies collapsed by default (line 30)
   - What's unclear: Impact on new users who don't know thresholds
   - Recommendation: Follow CONTEXT.md (collapsed by default), add inline "near threshold" indicators when within 1 point of next level

4. **What migration path for evidence_data with complex nested structures (e.g., evidence items arrays)?**
   - What we know: ClinGen uses `evidence_items` arrays, other schemas may use flat structures
   - What's unclear: Whether to normalize on load (complex) or handle both formats (more code)
   - Recommendation: Backend normalization (single migration pass), frontend only handles normalized format

## Sources

### Primary (HIGH confidence)
- [VueUse watchDebounced](https://vueuse.org/shared/watchdebounced/) - Debouncing composable API and options
- [Vuetify 3 Skeleton Loader](https://vuetifyjs.com/en/components/skeleton-loaders/) - Component API and built-in types
- Codebase files:
  - `frontend/src/components/dynamic/DynamicForm.vue` - Current implementation, validation pattern
  - `frontend/src/composables/useScoring.js` - ClinGen scoring composable
  - `backend/app/scoring/registry.py` - Scoring engine architecture
  - `backend/app/core/schema_validator.py` - Score calculation integration with validation

### Secondary (MEDIUM confidence)
- [Vue Debounce Guide (LogRocket)](https://blog.logrocket.com/debounce-throttle-vue/) - Patterns and best practices
- [Vue 3 Performance Pitfalls (Simform, Dec 2025)](https://medium.com/simform-engineering/7-vue-3-performance-pitfalls-that-quietly-derail-your-app-33c7180d68d4) - Watch optimization, debounce strategies
- [Feature Flags in Vue.js (ConfigCat)](https://configcat.com/blog/2022/01/28/how-to-use-feature-flag-in-vuejs/) - Integration patterns
- [Progressive Migration Backbone to Vue (Snipcart)](https://snipcart.com/blog/progressive-migration-backbone-vuejs-refactoring) - Strangler fig pattern for component replacement

### Tertiary (LOW confidence)
- [Vue 3 Composition API Real-time Validation (Medium)](https://medium.com/@lucina12/vue-js-202-the-power-of-vue-3-composition-api-reactivity-system-a-deep-dive-0b845d696e54) - General patterns, not specific to scoring
- [Skeleton Loading with Vue (Markus Oberlehner)](https://markus.oberlehner.net/blog/skeleton-loading-animation-with-vue) - Animation techniques (Vue 2 era, some patterns outdated)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, versions verified in package.json/pyproject.toml
- Architecture: HIGH - Patterns verified in existing codebase, Vuetify 3 documentation authoritative
- Pitfalls: HIGH - Derived from codebase anti-patterns and Vue 3 performance best practices
- Open questions: MEDIUM - Some decisions require user testing or performance measurement

**Research date:** 2026-01-23
**Valid until:** 60 days (stable technologies, minor version updates expected)
**Codebase context:** Gene Curator v0.3.0, Vue 3.4+, Vuetify 3.5+
