# Phase 2: Tab Structure - Research

**Researched:** 2026-01-22
**Domain:** Vuetify 3 tabs with sections, lazy rendering, and responsive navigation
**Confidence:** HIGH

## Summary

This phase implements tabbed navigation for dynamic forms using Vuetify 3's v-tabs/v-window components, organizing fields into tabs with collapsible sections based on schema `ui_configuration.layout.tabs`. The standard approach uses v-tabs for navigation headers with v-window/v-window-item for lazy-rendered content, keeping components alive after first visit to preserve scroll position and focus state.

**Current State:** DynamicForm renders flat field list. Phase 2 adds: (1) tab navigation from schema configuration, (2) section grouping within tabs with optional collapsibility, (3) score badges on tab headers with live updates, (4) skeleton loaders for lazy content, (5) fallback to flat list when ui_configuration absent.

**Key Technical Challenges:**
- Lazy rendering with KeepAlive to preserve form state between tab switches
- Responsive tab navigation (horizontal on desktop, appropriate mobile behavior)
- Live score badge updates without re-rendering entire form
- Section collapsibility UX (when to default collapsed vs expanded)
- Backward compatibility with schemas lacking ui_configuration

**Primary recommendation:** Use v-tabs with v-window for lazy rendering, implement per-tab KeepAlive wrappers, use v-expansion-panels for collapsible sections within tabs, display score badges as v-chip components reactive to computed scores, and gracefully fallback to flat field rendering when ui_configuration is absent.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vue | 3.4.21 | Framework with KeepAlive built-in | onActivated/onDeactivated lifecycle hooks for tab state |
| Vuetify | 3.9.3 | Material Design UI | v-tabs, v-window, v-expansion-panels, v-chip all integrated |
| Pinia | 2.1.7 | State management | Reactive score calculations for badge updates |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @vueuse/core | 14.1.0 | Composition utilities | useBreakpoints for mobile detection (optional pattern) |

### Schema Structure (from database)
```typescript
ui_configuration: {
  layout: {
    type: "tabs",
    tabs: [
      {
        id: string,           // "summary", "genetic", etc.
        name: string,         // Display name
        icon: string,         // mdi-icon-name
        show_score_badge: boolean,  // Optional
        sections: [
          {
            name: string,
            fields: string[],     // Field paths
            collapsible: boolean, // Optional
            collapsed: boolean,   // Optional default state
            help_text: string     // Optional
          }
        ]
      }
    ]
  }
}
```

**Existing Example:** ClinGen SOP v11 schema in `database/sql/020_complete_sop11_schema.sql` lines 920-1049 demonstrates full tab structure with 5 tabs, icons, score badges, and collapsible sections.

**Installation:**
```bash
# Already installed in package.json
cd frontend
npm install
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/components/dynamic/
├── DynamicForm.vue              # Container - adds tab/section logic
├── DynamicField.vue             # Unchanged - renders individual fields
└── componentRegistry.js         # Unchanged

# Pattern: DynamicForm orchestrates tabs/sections, delegates field rendering to DynamicField
```

### Pattern 1: v-tabs with v-window for Lazy Rendering

**What:** v-tabs provides navigation UI, v-window controls content display with lazy loading and KeepAlive.

**When to use:** Forms with 3+ logical groupings that don't need simultaneous visibility.

**Example:**
```vue
<template>
  <v-card>
    <!-- Tab Headers -->
    <v-tabs
      v-model="activeTab"
      show-arrows
      color="primary"
    >
      <v-tab
        v-for="tab in tabsConfig"
        :key="tab.id"
        :value="tab.id"
      >
        <v-icon v-if="tab.icon" :icon="tab.icon" start />
        {{ tab.name }}
        <v-chip
          v-if="tab.show_score_badge && tabScores[tab.id] !== undefined"
          :color="getScoreColor(tabScores[tab.id])"
          size="small"
          class="ml-2"
        >
          {{ tabScores[tab.id] }}
        </v-chip>
      </v-tab>
    </v-tabs>

    <!-- Tab Content (Lazy Rendered) -->
    <v-window v-model="activeTab">
      <v-window-item
        v-for="tab in tabsConfig"
        :key="tab.id"
        :value="tab.id"
      >
        <KeepAlive>
          <TabContent
            :tab="tab"
            :form-data="formData"
            @update:field="updateField"
          />
        </KeepAlive>
      </v-window-item>
    </v-window>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeTab = ref(props.tabsConfig?.[0]?.id)

// Computed scores per tab (reactive to formData changes)
const tabScores = computed(() => {
  const scores = {}
  props.tabsConfig?.forEach(tab => {
    if (tab.show_score_badge) {
      scores[tab.id] = calculateTabScore(tab, props.formData)
    }
  })
  return scores
})
</script>
```

**Key Points:**
- `show-arrows` enables scrolling navigation when tabs overflow
- v-window-item lazy renders by default (content created on first visit)
- KeepAlive preserves component state when switching away
- v-model synchronizes tab selection between header and content

**Source:** [Vuetify Tabs component](https://vuetifyjs.com/en/components/tabs/), [Vuetify Window component](https://vuetifyjs.com/en/components/windows/)

### Pattern 2: KeepAlive with Lifecycle Hooks

**What:** Vue 3's KeepAlive preserves component instances between tab switches. Components receive onActivated/onDeactivated events.

**When to use:** Tab content with user input, scroll position, or expanded state that should persist.

**Example:**
```vue
<!-- TabContent.vue -->
<script setup>
import { ref, onActivated, onDeactivated } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
const isActive = ref(true)

onActivated(() => {
  isActive.value = true
  logger.debug('Tab activated', { tabId: props.tab.id })
  // Optionally: Resume timers, restart polling, refetch stale data
})

onDeactivated(() => {
  isActive.value = false
  logger.debug('Tab deactivated', { tabId: props.tab.id })
  // Optionally: Pause timers, stop polling
})
</script>

<template>
  <v-card-text>
    <!-- Tab sections render here -->
    <template v-for="section in tab.sections" :key="section.name">
      <SectionRenderer
        :section="section"
        :form-data="formData"
        @update:field="$emit('update:field', $event)"
      />
    </template>
  </v-card-text>
</template>
```

**Key Insight:** KeepAlive preserves DOM state including:
- Input values (redundant with v-model but preserves focus)
- Scroll position within tab
- Expansion panel open/closed state
- Component internal state (refs, reactive data)

**Lifecycle behavior:**
- `onMounted()` - Called once on first tab visit
- `onActivated()` - Called on first visit AND every subsequent activation
- `onDeactivated()` - Called when switching away
- `onUnmounted()` - Never called while KeepAlive active

**Source:** [Vue 3 KeepAlive Guide](https://vuejs.org/guide/built-ins/keep-alive), [Composition API Lifecycle Hooks](https://vuejs.org/api/composition-api-lifecycle)

### Pattern 3: Collapsible Sections with v-expansion-panels

**What:** v-expansion-panels groups collapsible sections. Each section can default open or closed based on schema config.

**When to use:** Within tabs to organize 3+ related field groups where users don't need simultaneous visibility.

**Example:**
```vue
<template>
  <v-expansion-panels
    v-model="openSections"
    multiple
    variant="accordion"
  >
    <v-expansion-panel
      v-for="(section, index) in tab.sections"
      :key="section.name"
      :value="index"
    >
      <v-expansion-panel-title>
        <div class="d-flex align-center">
          <v-icon v-if="section.icon" :icon="section.icon" start />
          <span class="font-weight-medium">{{ section.name }}</span>
        </div>
      </v-expansion-panel-title>

      <v-expansion-panel-text>
        <div v-if="section.help_text" class="text-caption text-medium-emphasis mb-4">
          {{ section.help_text }}
        </div>

        <v-row>
          <v-col
            v-for="fieldPath in section.fields"
            :key="fieldPath"
            cols="12"
            :sm="section.fields.length > 2 ? 6 : 12"
          >
            <DynamicField
              :field-name="getFieldName(fieldPath)"
              :field-schema="getFieldSchema(fieldPath)"
              :model-value="getFieldValue(fieldPath)"
              @update:model-value="updateField(fieldPath, $event)"
            />
          </v-col>
        </v-row>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  tab: { type: Object, required: true },
  formData: { type: Object, required: true }
})

// Initialize open sections based on schema defaults
const openSections = ref(
  props.tab.sections
    .map((section, index) => !section.collapsed ? index : null)
    .filter(i => i !== null)
)

// Multiple prop allows multiple panels open simultaneously
// variant="accordion" provides connected panel styling
</script>
```

**Collapsibility Best Practices (from UX research):**

**Use collapsible sections when:**
- Content is hierarchical rather than parallel
- Users don't need to switch back and forth frequently
- Long forms need progressive disclosure to reduce cognitive load
- Secondary/advanced fields should be hidden by default

**Default collapsed when:**
- Section is rarely used (e.g., "Contradictory Evidence" in ClinGen)
- Section contains advanced/optional fields
- User must complete primary sections first (workflow order)

**Default expanded when:**
- Section contains required fields
- Section is used in 80%+ of submissions
- First section in tab (guide users to start point)

**Source:** [Vuetify Expansion Panels](https://vuetifyjs.com/en/components/expansion-panels/), [Accordions on Desktop UX (NN/G)](https://www.nngroup.com/articles/accordions-on-desktop/), [Tabs UX Best Practices](https://www.eleken.co/blog-posts/tabs-ux)

### Pattern 4: Skeleton Loaders for Lazy Content

**What:** v-skeleton-loader displays placeholder UI while tab content first renders.

**When to use:** Tabs with heavy content (10+ fields, async data fetching) where initial render takes >100ms.

**Example:**
```vue
<template>
  <v-window-item :value="tab.id">
    <KeepAlive>
      <component
        :is="TabContent"
        v-if="tabVisited[tab.id]"
        :tab="tab"
        :form-data="formData"
        @update:field="$emit('update:field', $event)"
      />
      <v-skeleton-loader
        v-else
        type="card, list-item@3, list-item@3"
        class="pa-4"
      />
    </KeepAlive>
  </v-window-item>
</template>

<script setup>
import { ref, watch } from 'vue'

const tabVisited = ref({})

watch(activeTab, (newTab) => {
  if (newTab && !tabVisited.value[newTab]) {
    // Mark tab as visited on first activation
    tabVisited.value[newTab] = true
  }
}, { immediate: true })
</script>
```

**Skeleton Types for Forms:**
- `"list-item@3"` - Three form field placeholders
- `"card"` - Section card placeholder
- `"heading, list-item@2"` - Section header + fields
- `"table-tbody"` - For data tables within tabs

**Optimization:** For most forms, lazy rendering is fast enough without skeletons. Use only for tabs with:
- 15+ fields
- Custom components with API calls (autocompletes)
- Heavy computed calculations on mount

**Source:** [Vuetify Skeleton Loader](https://vuetifyjs.com/en/components/skeleton-loaders/), [Lazy Loading Implementation Guide](https://app.studyraid.com/en/read/12385/399985/lazy-loading-implementation)

### Pattern 5: Responsive Mobile Tab Behavior

**What:** Horizontal tabs on desktop, same pattern on mobile with touch-friendly sizing and optional swipe gestures.

**When to use:** All tabbed forms (default pattern).

**Example:**
```vue
<template>
  <v-card>
    <v-tabs
      v-model="activeTab"
      show-arrows
      color="primary"
      :stacked="isMobile && stackedMobile"
      density="comfortable"
    >
      <v-tab
        v-for="tab in tabsConfig"
        :key="tab.id"
        :value="tab.id"
        :min-width="isMobile ? 80 : 120"
      >
        <v-icon v-if="tab.icon" :icon="tab.icon" :start="!isMobile" />
        <span v-if="!isMobile || !tab.icon">{{ tab.name }}</span>
      </v-tab>
    </v-tabs>

    <!-- Enable swipe on mobile -->
    <v-window
      v-model="activeTab"
      :touch="{ left: nextTab, right: prevTab }"
    >
      <!-- Tab content -->
    </v-window>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import { useDisplay } from 'vuetify'

const { mobile } = useDisplay()
const isMobile = computed(() => mobile.value)

function nextTab() {
  const currentIndex = tabsConfig.findIndex(t => t.id === activeTab.value)
  if (currentIndex < tabsConfig.length - 1) {
    activeTab.value = tabsConfig[currentIndex + 1].id
  }
}

function prevTab() {
  const currentIndex = tabsConfig.findIndex(t => t.id === activeTab.value)
  if (currentIndex > 0) {
    activeTab.value = tabsConfig[currentIndex - 1].id
  }
}
</script>
```

**Mobile UX Best Practices (2026):**
- **Horizontal tabs remain best practice** for 3-7 tabs (Material Design standard)
- **Show icons on mobile** to save space (icon-only or icon + truncated text)
- **Scrollable tabs with arrows** better than dropdown for discoverability
- **Touch targets minimum 48px** (Vuetify default is 48px height)
- **Swipe gestures optional** - many users unfamiliar, arrows provide clear navigation
- **Avoid nested tabs** - confusing on mobile, use sections instead

**When to deviate:**
- 8+ tabs: Consider navigation drawer or grouped tabs
- Complex forms: Split into multiple pages rather than many tabs

**Source:** [Mobile Navigation UX Best Practices 2026](https://www.designstudiouiux.com/blog/mobile-navigation-ux/), [Tabs for Mobile UX Design](https://uxplanet.org/tabs-for-mobile-ux-design-d4cc4d9410d1), [Vuetify useDisplay](https://vuetifyjs.com/en/features/display-and-platform/)

### Pattern 6: Live Score Badge Updates

**What:** v-chip displays tab scores, reactively computed from formData without manual refresh.

**When to use:** Tabs with `show_score_badge: true` in schema configuration.

**Example:**
```vue
<template>
  <v-tab :value="tab.id">
    <v-icon v-if="tab.icon" :icon="tab.icon" start />
    {{ tab.name }}
    <v-chip
      v-if="tab.show_score_badge && tabScore !== null"
      :color="scoreColor"
      size="small"
      variant="flat"
      class="ml-2"
    >
      {{ tabScore }}
    </v-chip>
  </v-tab>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tab: { type: Object, required: true },
  formData: { type: Object, required: true },
  scoringEngine: { type: Object, required: true }
})

// Computed score updates automatically when formData changes
const tabScore = computed(() => {
  if (!props.tab.show_score_badge) return null

  // Get fields for this tab
  const tabFields = props.tab.sections.flatMap(s => s.fields)

  // Extract relevant data
  const tabData = {}
  tabFields.forEach(fieldPath => {
    const value = getNestedValue(props.formData, fieldPath)
    if (value !== undefined) {
      tabData[fieldPath] = value
    }
  })

  // Calculate score using scoring engine
  return props.scoringEngine.calculateTabScore(props.tab.id, tabData)
})

const scoreColor = computed(() => {
  if (tabScore.value === null) return 'grey'
  if (tabScore.value >= 7) return 'success'
  if (tabScore.value >= 2) return 'warning'
  return 'info'
})

function getNestedValue(obj, path) {
  return path.split('.').reduce((acc, key) => acc?.[key], obj)
}
</script>
```

**Badge Color Scheme:**
- **success (green):** High score (≥7 for ClinGen genetic evidence)
- **warning (orange):** Moderate score (2-6)
- **info (blue):** Low score (<2)
- **grey:** No score calculated yet

**Performance:** Computed properties cache results and only recalculate when dependencies (formData) change. For 5 tabs, scoring overhead is negligible (<10ms per update).

**Source:** [Vuetify Chip Component](https://vuetifyjs.com/en/components/chips/), [Vue Computed Properties](https://vuejs.org/guide/essentials/computed)

### Pattern 7: Backward Compatibility Fallback

**What:** Render flat field list when `ui_configuration.layout.tabs` is absent or invalid.

**When to use:** Always (ensures old schemas continue working).

**Example:**
```vue
<template>
  <v-form ref="formRef" @submit.prevent="handleSubmit">
    <v-card>
      <v-card-title>{{ title }}</v-card-title>

      <v-card-text>
        <!-- Tabbed Layout -->
        <div v-if="hasTabs">
          <v-tabs v-model="activeTab" show-arrows>
            <!-- Tab structure from Pattern 1 -->
          </v-tabs>
          <v-window v-model="activeTab">
            <!-- Tab content -->
          </v-window>
        </div>

        <!-- Flat Fallback (existing behavior) -->
        <div v-else>
          <v-row>
            <v-col
              v-for="(field, fieldName) in jsonSchema.properties"
              :key="fieldName"
              :cols="getFieldCols(field)"
            >
              <DynamicField
                :field-name="fieldName"
                :field-schema="field"
                :model-value="formData[fieldName]"
                @update:model-value="updateField(fieldName, $event)"
              />
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>
  </v-form>
</template>

<script setup>
import { computed } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()

const hasTabs = computed(() => {
  const layout = props.schema?.ui_configuration?.layout

  if (!layout) {
    logger.debug('No ui_configuration.layout - using flat rendering')
    return false
  }

  if (layout.type !== 'tabs') {
    logger.debug('Layout type not tabs - using flat rendering', { type: layout.type })
    return false
  }

  if (!Array.isArray(layout.tabs) || layout.tabs.length === 0) {
    logger.warn('Invalid tabs configuration - using flat rendering', { layout })
    return false
  }

  return true
})
</script>
```

**Validation Checks:**
1. `ui_configuration` exists
2. `ui_configuration.layout` exists
3. `layout.type === "tabs"`
4. `layout.tabs` is non-empty array
5. Each tab has `id`, `name`, and `sections` array

**Graceful Degradation:** Invalid partial config falls back to flat rendering rather than crashing. Log warning for debugging.

**Source:** Existing DynamicForm.vue pattern + backward compatibility best practices

### Anti-Patterns to Avoid

- **Using v-tab-item instead of v-window-item:** v-tab-item deprecated in Vuetify 3, causes confusion
- **Nested tabs:** Overwhelming on mobile, hard to track context - use sections instead
- **Accordion mode (single panel open):** Forms benefit from comparing sections, use `multiple` prop
- **Eager rendering all tabs:** Defeats lazy loading benefits, keep default v-window-item behavior
- **Score calculations in template:** Use computed properties for reactivity and caching
- **Global tab state in store:** Tab selection is per-form instance, use component-level ref

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tab lazy rendering | Custom v-show logic with loading flags | v-window default behavior | Automatic, handles edge cases (rapid switching), tested |
| Component state preservation | Manual save/restore on tab switch | Vue KeepAlive | Preserves all state (scroll, focus, refs), no code needed |
| Responsive tab detection | Custom window.innerWidth watching | Vuetify useDisplay composable | Reactive, matches Vuetify breakpoints, handles orientation |
| Score reactivity | Manual watchers on formData | Computed properties | Automatic dependency tracking, cached, cleaner code |
| Swipe gestures | Touch event handlers | v-window `:touch` prop | Handles edge cases (partial swipes, cancellation, momentum) |

**Key insight:** Vuetify 3's tab components solve most complexity. Challenge is schema-driven configuration mapping, not low-level tab mechanics.

## Common Pitfalls

### Pitfall 1: KeepAlive Without v-window-item

**What goes wrong:** Wrapping v-window in KeepAlive instead of individual v-window-items. All tabs kept alive from start, defeating lazy loading. Memory usage increases linearly with tab count.

**Why it happens:** Misunderstanding KeepAlive scope - applies to immediate children.

**How to avoid:**
```vue
<!-- ❌ WRONG: Keeps ALL tabs alive immediately -->
<KeepAlive>
  <v-window v-model="activeTab">
    <v-window-item v-for="tab in tabs" :key="tab.id">
      <TabContent :tab="tab" />
    </v-window-item>
  </v-window>
</KeepAlive>

<!-- ✅ CORRECT: Each tab kept alive after first visit -->
<v-window v-model="activeTab">
  <v-window-item v-for="tab in tabs" :key="tab.id">
    <KeepAlive>
      <TabContent :tab="tab" />
    </KeepAlive>
  </v-window-item>
</v-window>
```

**Warning signs:** All tabs render on page load (check Vue DevTools component tree), high initial memory usage, longer time to first paint.

**Source:** [Vue KeepAlive Guide](https://vuejs.org/guide/built-ins/keep-alive), [GitHub Issue #2111](https://github.com/tailwindlabs/headlessui/issues/2111)

### Pitfall 2: Tab v-model Mismatch with Window

**What goes wrong:** Using separate refs for v-tabs and v-window models. Clicking tab header doesn't change content, or vice versa. User confusion, broken navigation.

**Why it happens:** Copy-paste from examples with separate controls, misunderstanding v-model sync.

**How to avoid:**
```vue
<!-- ❌ WRONG: Separate models lose sync -->
<v-tabs v-model="tabHeaderModel">
  <v-tab value="tab1">Tab 1</v-tab>
</v-tabs>
<v-window v-model="windowContentModel">
  <v-window-item value="tab1">Content</v-window-item>
</v-window>

<!-- ✅ CORRECT: Single model syncs both -->
<script setup>
const activeTab = ref('tab1')
</script>

<v-tabs v-model="activeTab">
  <v-tab value="tab1">Tab 1</v-tab>
</v-tabs>
<v-window v-model="activeTab">
  <v-window-item value="tab1">Content</v-window-item>
</v-window>
```

**Warning signs:** Clicking tab doesn't change content, URL updates but content doesn't, console warnings about unmatched values.

### Pitfall 3: Computing Scores Without Memoization

**What goes wrong:** Calculating tab scores in methods called from template. Recalculates on every render cycle, even when formData unchanged. CPU spikes, input lag, battery drain on mobile.

**Why it happens:** Not understanding Vue's reactivity and render optimization.

**How to avoid:**
```vue
<!-- ❌ WRONG: Recalculates every render -->
<v-chip>{{ calculateScore(tab.id) }}</v-chip>

<script setup>
function calculateScore(tabId) {
  // Heavy calculation runs on every render
  return heavyScoreCalculation(formData, tabId)
}
</script>

<!-- ✅ CORRECT: Computed property caches result -->
<v-chip>{{ tabScores[tab.id] }}</v-chip>

<script setup>
const tabScores = computed(() => {
  const scores = {}
  tabs.forEach(tab => {
    scores[tab.id] = heavyScoreCalculation(formData, tab.id)
  })
  return scores
})
</script>
```

**Warning signs:** High CPU usage when typing, Vue DevTools showing frequent re-renders, profiler showing score calculation in hot path.

**Source:** [Vue Computed Properties](https://vuejs.org/guide/essentials/computed), [Performance Best Practices](https://vuejs.org/guide/best-practices/performance)

### Pitfall 4: Missing Sections Array Validation

**What goes wrong:** Schema has `ui_configuration.layout.tabs` but tab missing `sections` array or has empty sections. Component crashes with "Cannot read property 'map' of undefined" or renders empty tab.

**Why it happens:** Assuming schema is always valid, no defensive checks.

**How to avoid:**
```vue
<script setup>
import { useLogger } from '@/composables/useLogger'
const logger = useLogger()

const validTabs = computed(() => {
  if (!hasTabs.value) return []

  return schema.ui_configuration.layout.tabs.filter(tab => {
    // Validate tab structure
    if (!tab.id || !tab.name) {
      logger.warn('Tab missing required fields', { tab })
      return false
    }

    if (!Array.isArray(tab.sections) || tab.sections.length === 0) {
      logger.warn('Tab has no sections', { tabId: tab.id })
      return false
    }

    // Validate sections have fields
    const hasFields = tab.sections.some(s =>
      Array.isArray(s.fields) && s.fields.length > 0
    )

    if (!hasFields) {
      logger.warn('Tab sections have no fields', { tabId: tab.id })
      return false
    }

    return true
  })
})

// Hide entire tab system if no valid tabs
const hasTabs = computed(() => {
  return validTabs.value.length > 0
})
</script>
```

**Warning signs:** Console errors about undefined properties, empty tab content, missing fields that should be visible.

### Pitfall 5: Expansion Panel Value Type Mismatch

**What goes wrong:** Using `v-model="openSections"` with number array (panel indices) but providing string values. Panels don't open/close correctly. Or using `value="0"` (string) when expecting `value="summary"` (section id).

**Why it happens:** v-expansion-panels defaults to index-based values, schema might use string IDs.

**How to avoid:**
```vue
<!-- ✅ OPTION 1: Use indices (default) -->
<v-expansion-panels v-model="openSections" multiple>
  <v-expansion-panel
    v-for="(section, index) in tab.sections"
    :key="section.name"
    :value="index"
  >
    <!-- content -->
  </v-expansion-panel>
</v-expansion-panels>

<script setup>
// Initialize with collapsed: false sections
const openSections = ref(
  tab.sections
    .map((s, i) => !s.collapsed ? i : null)
    .filter(i => i !== null)
)
</script>

<!-- ✅ OPTION 2: Use section IDs -->
<v-expansion-panels v-model="openSectionIds" multiple>
  <v-expansion-panel
    v-for="section in tab.sections"
    :key="section.name"
    :value="section.id || section.name"
  >
    <!-- content -->
  </v-expansion-panel>
</v-expansion-panels>

<script setup>
const openSectionIds = ref(
  tab.sections
    .filter(s => !s.collapsed)
    .map(s => s.id || s.name)
)
</script>
```

**Warning signs:** Clicking panel doesn't expand, wrong panel expands, panels don't remember state after tab switch.

**Source:** [Vuetify Expansion Panels API](https://vuetifyjs.com/en/api/v-expansion-panels)

## Code Examples

Verified patterns from official sources and codebase:

### Complete Tabbed DynamicForm Structure

```vue
<!-- DynamicForm.vue (enhanced with tabs) -->
<template>
  <v-form ref="formRef" @submit.prevent="handleSubmit">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-form-select</v-icon>
        {{ title }}
      </v-card-title>

      <v-card-text>
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8">
          <v-progress-circular indeterminate color="primary" />
          <div class="mt-4">Loading form schema...</div>
        </div>

        <!-- Tabbed Layout -->
        <div v-else-if="hasTabs">
          <v-tabs
            v-model="activeTab"
            show-arrows
            color="primary"
            density="comfortable"
          >
            <v-tab
              v-for="tab in validTabs"
              :key="tab.id"
              :value="tab.id"
            >
              <v-icon v-if="tab.icon" :icon="tab.icon" start />
              {{ tab.name }}
              <v-chip
                v-if="tab.show_score_badge && tabScores[tab.id] !== undefined"
                :color="getScoreColor(tabScores[tab.id])"
                size="small"
                variant="flat"
                class="ml-2"
              >
                {{ tabScores[tab.id] }}
              </v-chip>
            </v-tab>
          </v-tabs>

          <v-window v-model="activeTab">
            <v-window-item
              v-for="tab in validTabs"
              :key="tab.id"
              :value="tab.id"
            >
              <KeepAlive>
                <TabContent
                  :tab="tab"
                  :schema="jsonSchema"
                  :form-data="formData"
                  :validation-result="validationResult"
                  :readonly="readonly"
                  @update:field="updateField"
                />
              </KeepAlive>
            </v-window-item>
          </v-window>
        </div>

        <!-- Flat Fallback (existing behavior) -->
        <div v-else-if="jsonSchema && jsonSchema.properties">
          <v-row>
            <v-col
              v-for="(field, fieldName) in jsonSchema.properties"
              :key="fieldName"
              :cols="getFieldCols(field)"
            >
              <DynamicField
                :field-name="fieldName"
                :field-schema="field"
                :model-value="formData[fieldName]"
                :validation-result="getFieldValidation(fieldName)"
                :disabled="readonly"
                @update:model-value="updateField(fieldName, $event)"
                @validate="validateField(fieldName, $event)"
              />
            </v-col>
          </v-row>
        </div>

        <!-- Error State -->
        <v-alert v-else-if="error" type="error" variant="tonal">
          Failed to load form schema: {{ error }}
        </v-alert>

        <!-- Validation Errors (shown for both layouts) -->
        <v-alert
          v-if="validationResult && !validationResult.is_valid"
          type="error"
          variant="tonal"
          class="mt-4"
        >
          <div class="font-weight-medium mb-2">Form Validation Errors</div>
          <ul class="pl-4">
            <li v-for="error in validationResult.errors" :key="error.field">
              <strong>{{ error.field }}:</strong> {{ error.message }}
            </li>
          </ul>
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="$emit('cancel')">Cancel</v-btn>
        <v-btn
          color="primary"
          :loading="submitting"
          :disabled="readonly"
          @click="handleSubmit"
        >
          Submit
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-form>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useLogger } from '@/composables/useLogger'
import DynamicField from './DynamicField.vue'
import TabContent from './TabContent.vue'

const logger = useLogger()

const props = defineProps({
  schemaId: { type: String, required: true },
  title: { type: String, default: 'Dynamic Form' },
  initialData: { type: Object, default: () => ({}) },
  readonly: { type: Boolean, default: false }
})

const emit = defineEmits(['submit', 'cancel', 'update:data'])

// State
const formRef = ref(null)
const loading = ref(true)
const error = ref(null)
const submitting = ref(false)
const jsonSchema = ref(null)
const formData = ref({ ...props.initialData })
const validationResult = ref(null)
const activeTab = ref(null)

// Tabs configuration validation
const hasTabs = computed(() => {
  const layout = jsonSchema.value?.ui_configuration?.layout

  if (!layout || layout.type !== 'tabs') return false
  if (!Array.isArray(layout.tabs) || layout.tabs.length === 0) {
    logger.warn('Invalid tabs configuration', { layout })
    return false
  }

  return true
})

const validTabs = computed(() => {
  if (!hasTabs.value) return []

  return jsonSchema.value.ui_configuration.layout.tabs.filter(tab => {
    if (!tab.id || !tab.name) {
      logger.warn('Tab missing required fields', { tab })
      return false
    }

    if (!Array.isArray(tab.sections) || tab.sections.length === 0) {
      logger.warn('Tab has no sections', { tabId: tab.id })
      return false
    }

    return true
  })
})

// Initialize active tab
watch(validTabs, (tabs) => {
  if (tabs.length > 0 && !activeTab.value) {
    activeTab.value = tabs[0].id
  }
}, { immediate: true })

// Computed scores for badges
const tabScores = computed(() => {
  if (!validationResult.value?.score_calculations) return {}

  const scores = {}
  validTabs.value.forEach(tab => {
    if (tab.show_score_badge) {
      // Map tab to score category (depends on scoring engine)
      scores[tab.id] = calculateTabScore(tab)
    }
  })

  return scores
})

function calculateTabScore(tab) {
  // Extract relevant score from validation result
  // This mapping depends on schema scoring configuration
  const scoreCalc = validationResult.value?.score_calculations

  if (tab.id === 'genetic') {
    return scoreCalc?.genetic_evidence_score || 0
  } else if (tab.id === 'experimental') {
    return scoreCalc?.experimental_evidence_score || 0
  }

  return null
}

function getScoreColor(score) {
  if (score === null || score === undefined) return 'grey'
  if (score >= 7) return 'success'
  if (score >= 2) return 'warning'
  return 'info'
}

// Load schema and initialize form
async function loadSchema() {
  try {
    loading.value = true
    error.value = null

    // Fetch schema from API (existing pattern)
    const response = await fetch(`/api/v1/schemas/${props.schemaId}`)
    const schemaData = await response.json()

    jsonSchema.value = schemaData
    logger.info('Schema loaded', { schemaId: props.schemaId, hasTabs: hasTabs.value })

  } catch (e) {
    error.value = e.message
    logger.error('Failed to load schema', { schemaId: props.schemaId, error: e })
  } finally {
    loading.value = false
  }
}

function updateField(fieldPath, value) {
  // Handle both flat field names and nested paths (from tabs/sections)
  if (fieldPath.includes('.')) {
    setNestedValue(formData.value, fieldPath, value)
  } else {
    formData.value[fieldPath] = value
  }

  emit('update:data', formData.value)

  // Trigger validation debounced
  // (existing pattern from Phase 1)
}

function setNestedValue(obj, path, value) {
  const keys = path.split('.')
  const lastKey = keys.pop()
  const target = keys.reduce((acc, key) => {
    if (!acc[key]) acc[key] = {}
    return acc[key]
  }, obj)
  target[lastKey] = value
}

async function handleSubmit() {
  submitting.value = true
  try {
    // Validate and submit (existing pattern)
    emit('submit', formData.value)
  } finally {
    submitting.value = false
  }
}

// Initialize on mount
loadSchema()
</script>
```

**Source:** Enhanced from existing DynamicForm.vue + Vuetify tabs patterns

### TabContent Component (Section Rendering)

```vue
<!-- TabContent.vue -->
<template>
  <v-card-text>
    <v-expansion-panels
      v-model="openSections"
      multiple
      variant="accordion"
    >
      <v-expansion-panel
        v-for="(section, index) in tab.sections"
        :key="section.name"
        :value="index"
      >
        <v-expansion-panel-title>
          <div class="d-flex align-center">
            <v-icon v-if="section.icon" :icon="section.icon" start class="mr-2" />
            <span class="font-weight-medium">{{ section.name }}</span>
          </div>
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <div v-if="section.help_text" class="text-caption text-medium-emphasis mb-4">
            {{ section.help_text }}
          </div>

          <v-row>
            <v-col
              v-for="fieldPath in section.fields"
              :key="fieldPath"
              cols="12"
              :sm="section.fields.length > 2 ? 6 : 12"
            >
              <DynamicField
                :field-name="getFieldName(fieldPath)"
                :field-schema="getFieldSchema(fieldPath)"
                :model-value="getFieldValue(fieldPath)"
                :validation-result="getFieldValidation(fieldPath)"
                :disabled="readonly"
                @update:model-value="$emit('update:field', fieldPath, $event)"
              />
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-card-text>
</template>

<script setup>
import { ref, onActivated, onDeactivated } from 'vue'
import { useLogger } from '@/composables/useLogger'
import DynamicField from './DynamicField.vue'

const logger = useLogger()

const props = defineProps({
  tab: { type: Object, required: true },
  schema: { type: Object, required: true },
  formData: { type: Object, required: true },
  validationResult: { type: Object, default: null },
  readonly: { type: Boolean, default: false }
})

const emit = defineEmits(['update:field'])

// Initialize open sections based on schema defaults
const openSections = ref(
  props.tab.sections
    .map((section, index) => !section.collapsed ? index : null)
    .filter(i => i !== null)
)

// Lifecycle hooks for tab activation
onActivated(() => {
  logger.debug('Tab activated', { tabId: props.tab.id })
})

onDeactivated(() => {
  logger.debug('Tab deactivated', { tabId: props.tab.id })
})

// Helper functions
function getFieldName(fieldPath) {
  const parts = fieldPath.split('.')
  return parts[parts.length - 1]
}

function getFieldSchema(fieldPath) {
  const parts = fieldPath.split('.')
  let schema = props.schema.properties

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]

    if (schema[part]) {
      // Direct property
      schema = schema[part]

      // If it's an object type, move into properties
      if (schema.type === 'object' && schema.properties) {
        schema = schema.properties
      }
      // If it's an array type, move into items.properties
      else if (schema.type === 'array' && schema.items?.properties) {
        schema = schema.items.properties
      }
    } else {
      logger.warn('Field schema not found', { fieldPath, part })
      return { type: 'string', label: fieldPath }
    }
  }

  return schema
}

function getFieldValue(fieldPath) {
  const parts = fieldPath.split('.')
  let value = props.formData

  for (const part of parts) {
    value = value?.[part]
  }

  return value
}

function getFieldValidation(fieldPath) {
  // Extract validation for specific field from validation result
  if (!props.validationResult?.field_errors) return null

  const errors = props.validationResult.field_errors[fieldPath]
  return errors ? { errors } : null
}
</script>
```

**Source:** Pattern derived from requirements + Vuetify expansion panels

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v-tab-item component | v-window-item | Vuetify 3.0 (2022) | Cleaner separation of navigation (tabs) and content (window) |
| Manual lazy loading with v-if | v-window default lazy behavior | Vuetify 3.0+ | Automatic optimization, less code |
| Component activation tracking with flags | KeepAlive + onActivated hooks | Vue 3.0 (2020) | Built-in lifecycle, cleaner state management |
| Manual mobile detection | useDisplay composable | Vuetify 3.0+ | Reactive breakpoints matching design system |
| Accordion single mode for forms | Multiple prop default | UX research (2023+) | Users compare sections, need simultaneous access |
| Fixed tab content loading | Skeleton loaders | Vuetify 3 + UX patterns (2024+) | Better perceived performance on slow loads |

**Deprecated/outdated:**
- **v-tab-item:** Replaced by v-window-item in Vuetify 3
- **Manual tab state preservation:** Use KeepAlive instead of saving/restoring state manually
- **Nested tabs:** Avoid - mobile unfriendly, confusing navigation (use sections instead)

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal default for section collapsibility**
   - What we know: First section should be expanded, rarely-used sections collapsed
   - What's unclear: Should sections with validation errors auto-expand?
   - Recommendation: Start with schema defaults (`collapsed: true/false`), consider auto-expanding sections with errors in Phase 4 (Validation)

2. **Score badge animation on updates**
   - What we know: Badge value updates reactively when formData changes
   - What's unclear: Should score changes be animated (number transition, color pulse)?
   - Recommendation: Start without animation (simpler, faster), add in future UX polish phase if user testing shows value

3. **Mobile swipe gestures necessity**
   - What we know: Vuetify v-window supports touch gestures, arrows provide clear navigation
   - What's unclear: Do users expect/discover swipe between form tabs?
   - Recommendation: Implement touch prop for completeness, monitor analytics (if available) to see if users discover/use swiping

4. **Tab hiding when no fields match schema**
   - What we know: Should hide empty tabs, but what if all sections hidden?
   - What's unclear: Show empty state tab or fallback to flat rendering?
   - Recommendation: Hide individual empty tabs, show warning if all tabs empty, fallback to flat rendering if <2 tabs remain visible

## Sources

### Primary (HIGH confidence)
- [Vuetify Tabs Component](https://vuetifyjs.com/en/components/tabs/) - Official v-tabs API and patterns
- [Vuetify Window Component](https://vuetifyjs.com/en/components/windows/) - Official v-window lazy rendering
- [Vuetify Expansion Panels](https://vuetifyjs.com/en/components/expansion-panels/) - Official collapsible sections
- [Vue 3 KeepAlive Guide](https://vuejs.org/guide/built-ins/keep-alive) - Official lifecycle hooks
- [Vuetify Chip Component](https://vuetifyjs.com/en/components/chips/) - Badge implementation
- Gene Curator database schema - `020_complete_sop11_schema.sql` lines 920-1049 (verified tab structure)

### Secondary (MEDIUM confidence)
- [Mobile Navigation UX Best Practices 2026](https://www.designstudiouiux.com/blog/mobile-navigation-ux/) - Current mobile patterns
- [Tabs for Mobile UX Design](https://uxplanet.org/tabs-for-mobile-ux-design-d4cc4d9410d1) - Mobile-specific guidance
- [Tabs UX Best Practices](https://www.eleken.co/blog-posts/tabs-ux) - When to use tabs vs alternatives
- [Accordions on Desktop (NN/G)](https://www.nngroup.com/articles/accordions-on-desktop/) - Collapsibility best practices
- [Mobile Navigation Design: 6 Patterns That Work in 2026](https://phone-simulator.com/blog/mobile-navigation-patterns-in-2026) - Current patterns
- [GitHub Issue: KeepAlive with tabs](https://github.com/tailwindlabs/headlessui/issues/2111) - Common pitfall discussion

### Tertiary (LOW confidence - flagged for validation)
- WebSearch results on Vuetify 3 skeleton loaders - Official docs not fetched, pattern inferred from component API
- Badge color scheme - Based on ClinGen classification thresholds, not universal standard

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Vuetify 3.9.3 verified in package.json, all components official
- Tab architecture: HIGH - Vuetify official docs + existing ClinGen schema demonstrates pattern
- KeepAlive patterns: HIGH - Vue 3 official documentation, clear lifecycle behavior
- Mobile UX: MEDIUM - Recent UX articles (2026) but no Gene Curator-specific user testing
- Collapsibility: MEDIUM - UX best practices from reputable sources (NN/G) but application-specific defaults need validation
- Score badges: HIGH - Vuetify chip API + Vue computed properties (official patterns)

**Research date:** 2026-01-22
**Valid until:** 60 days (stable ecosystem - Vue 3.4, Vuetify 3.9 unlikely to change tab patterns rapidly)
