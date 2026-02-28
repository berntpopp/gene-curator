# Phase 3: Field Metadata - Research

**Researched:** 2026-01-22
**Domain:** Vuetify 3 form field metadata, Material Design UX patterns
**Confidence:** MEDIUM

## Summary

Field metadata enhances form usability by providing contextual help directly at the field level. Vuetify 3 supports rich metadata through props (hint, persistent-hint, prepend-inner-icon, append-inner-icon) and slots (prepend-inner, append-inner). Research shows that persistent hints significantly improve accessibility compared to disappearing on-focus hints, and help links for external documentation should open in new tabs to avoid disrupting workflow. Icon placement requires attention to contrast ratios (minimum 4.5:1 for dark gray on white) to meet WCAG accessibility standards. Tooltip implementation uses Vuetify's v-tooltip component within slots with recommended activation delays of 200-300ms to prevent visual noise.

**Key recommendations:**
- Use persistent-hint for all helper text (not placeholder-based hints that disappear)
- Implement tooltips via prepend-inner slot with v-tooltip wrapping v-icon
- Use dark gray icons (#7A7A7A or darker) for accessibility (4.5:1 contrast ratio)
- Open help links in new tabs with target="_blank" and rel="noopener noreferrer"
- Truncate hints longer than 100 characters with expandable toggle

**Primary recommendation:** Prioritize accessibility-first implementation with persistent hints, high-contrast icons, and slot-based tooltip composition.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vuetify 3 | 3.x | UI component framework | Already in project stack, provides comprehensive form field props and slots |
| Material Design Icons | latest | Icon library (mdi- prefix) | Integrated with Vuetify, 7200+ icons following Material Design guidelines |
| Vue 3 Composition API | 3.x | Reactive state management | Project standard for component logic |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vue-truncate-read-more | 3.x compatible | Text truncation with toggle | For long hints requiring show more/less functionality |
| @mdi/js | latest | MDI icon paths for tree-shaking | Optional optimization for production bundle size |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vuetify slots | Direct v-bind="$attrs" | Slots provide better control for tooltip composition, v-bind spreads all attrs |
| Persistent hints | On-focus hints (placeholders) | Persistent hints meet WCAG accessibility, placeholders disappear and strain memory |
| New tab links | Modal dialogs | New tabs preserve workflow state, modals require additional UI complexity |

**Installation:**
```bash
# vue-truncate-read-more if implementing hint truncation
cd frontend && npm install vue-truncate-read-more
```

## Architecture Patterns

### Recommended Field Metadata Schema Structure
```typescript
// Schema field_definitions structure (from database)
{
  "field_name": {
    "type": "string",
    "label": "Field Label",
    "icon": "mdi-information-outline",        // MDI icon name
    "hint": "Persistent helper text below field",
    "tooltip": "Additional context on icon hover",
    "helpUrl": "https://docs.example.com/field-help",
    "description": "Deprecated - use hint instead"
  }
}
```

### Pattern 1: Prepend Icon with Tooltip
**What:** Icon in prepend-inner slot with v-tooltip wrapper
**When to use:** When field has icon and tooltip properties defined
**Example:**
```vue
<template>
  <v-text-field
    v-model="modelValue"
    :label="fieldSchema.label"
    :hint="fieldSchema.hint"
    persistent-hint
  >
    <template v-slot:prepend-inner>
      <v-tooltip location="top" :open-delay="250">
        <template v-slot:activator="{ props }">
          <v-icon
            v-bind="props"
            :icon="fieldSchema.icon || 'mdi-information-outline'"
            color="grey-darken-1"
            size="small"
          />
        </template>
        <span>{{ fieldSchema.tooltip }}</span>
      </v-tooltip>
    </template>
  </v-text-field>
</template>
```
**Source:** [Vuetify CodePen Example](https://codepen.io/scp-nm/pen/NWKgKvL)

### Pattern 2: Help Link in Append Slot
**What:** Clickable help icon linking to external documentation
**When to use:** When field has helpUrl property defined
**Example:**
```vue
<template>
  <v-text-field
    v-model="modelValue"
    :label="fieldSchema.label"
  >
    <template v-slot:append-inner>
      <v-tooltip location="top" text="View documentation">
        <template v-slot:activator="{ props }">
          <v-icon
            v-bind="props"
            icon="mdi-help-circle-outline"
            color="primary"
            size="small"
            @click.stop="openHelpUrl"
            style="cursor: pointer;"
          />
        </template>
      </v-tooltip>
    </template>
  </v-text-field>
</template>

<script setup>
const openHelpUrl = () => {
  window.open(fieldSchema.helpUrl, '_blank', 'noopener,noreferrer')
}
</script>
```

### Pattern 3: Persistent Hint with Truncation
**What:** Long hints with show more/less toggle
**When to use:** When hint exceeds ~100 characters
**Example:**
```vue
<template>
  <v-text-field
    v-model="modelValue"
    :label="fieldSchema.label"
  >
    <template v-slot:details>
      <div class="text-caption text-medium-emphasis">
        <span v-if="!hintExpanded">
          {{ truncatedHint }}
          <a
            v-if="needsTruncation"
            @click.prevent="hintExpanded = true"
            class="text-primary"
          >
            show more
          </a>
        </span>
        <span v-else>
          {{ fieldSchema.hint }}
          <a
            @click.prevent="hintExpanded = false"
            class="text-primary"
          >
            show less
          </a>
        </span>
      </div>
    </template>
  </v-text-field>
</template>

<script setup>
import { ref, computed } from 'vue'

const HINT_TRUNCATE_LENGTH = 100
const hintExpanded = ref(false)

const needsTruncation = computed(() =>
  fieldSchema.hint && fieldSchema.hint.length > HINT_TRUNCATE_LENGTH
)

const truncatedHint = computed(() =>
  needsTruncation.value
    ? fieldSchema.hint.substring(0, HINT_TRUNCATE_LENGTH) + '...'
    : fieldSchema.hint
)
</script>
```

### Pattern 4: Vuetify 3 Tooltip Activation Pattern
**What:** v-tooltip with activator slot and proper delay
**When to use:** All tooltip implementations
**Example:**
```vue
<v-tooltip location="top" :open-delay="250" :close-delay="100">
  <template v-slot:activator="{ props }">
    <v-icon v-bind="props" icon="mdi-information" />
  </template>
  <span>Tooltip content</span>
</v-tooltip>
```
**Source:** Vuetify 3 uses activator slot pattern with props binding

### Anti-Patterns to Avoid
- **Using placeholder for hints:** Placeholders disappear on focus, violating WCAG accessibility guidelines and straining user memory
- **Light gray icons (#9C9C9C):** Fails 4.5:1 contrast requirement, use #7A7A7A or darker
- **Tooltip on help icon:** Help icons should be clickable only, no tooltip preview (reduces confusion)
- **Opening help in same tab:** Disrupts workflow, loses form state
- **v-bind="$attrs" spread:** Prevents fine-grained slot control for tooltips
- **On-focus hint display:** Accessibility issue - hints should be persistent

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tooltip positioning | Custom absolute positioning logic | Vuetify v-tooltip with location prop | Auto-adjusts based on viewport, handles edge cases |
| Text truncation | Manual substring + CSS ellipsis | vue-truncate-read-more or Vuetify details slot | Handles resize, word boundaries, accessibility |
| Icon color contrast | Eyeballing gray values | WCAG color contrast calculator | Must meet 4.5:1 ratio, subtle differences matter |
| Help link security | Just target="_blank" | target="_blank" + rel="noopener noreferrer" | Prevents window.opener exploits |
| Slot-based composition | Direct prop binding | Named slots with v-slot:activator | Required for tooltip + icon combination |

**Key insight:** Vuetify 3 slot architecture requires composition patterns (slots within slots) that aren't obvious from basic prop documentation. Tooltip activator pattern is non-negotiable for proper v-tooltip integration.

## Common Pitfalls

### Pitfall 1: Vuetify 3 Tooltip Activator Pattern Change
**What goes wrong:** Attempting to use Vuetify 2 syntax (v-on="on") fails in Vuetify 3
**Why it happens:** Vuetify 3 changed from { on } to { props } in activator slots
**How to avoid:** Use `v-bind="props"` pattern, not `v-on="on"`
**Warning signs:** Tooltips not appearing, console warnings about deprecated syntax
**Example:**
```vue
<!-- WRONG (Vuetify 2) -->
<template v-slot:activator="{ on }">
  <v-icon v-on="on">mdi-help</v-icon>
</template>

<!-- CORRECT (Vuetify 3) -->
<template v-slot:activator="{ props }">
  <v-icon v-bind="props">mdi-help</v-icon>
</template>
```
**Source:** [Vuetify Migration Guide](https://github.com/vuetifyjs/vuetify/issues/15922)

### Pitfall 2: Icon Color Contrast Accessibility
**What goes wrong:** Using light gray (#9C9C9C) for subtle icons fails WCAG 2.1 AA standards
**Why it happens:** Visual design preference for subtle icons conflicts with 4.5:1 contrast requirement
**How to avoid:** Use #7A7A7A or darker, or Vuetify color "grey-darken-1"
**Warning signs:** Accessibility audits fail, low vision users can't see icons
**Calculation:**
- Light gray #9C9C9C on white #FFFFFF = 2.7:1 (FAIL)
- Dark gray #7A7A7A on white #FFFFFF = 4.3:1 (PASS)
- #777777 or darker on white = 4.5:1+ (PASS)
**Source:** [WebAIM Contrast Checker](https://webaim.org/articles/contrast/)

### Pitfall 3: Persistent Hint vs Placeholder Confusion
**What goes wrong:** Using placeholder attribute instead of persistent-hint for helper text
**Why it happens:** Placeholders look cleaner when field is empty
**How to avoid:** Always use hint + persistent-hint props, never placeholder for essential guidance
**Warning signs:** Users clearing fields to re-read instructions, accessibility audit failures
**Evidence:** WCAG 2.1 requires labels and essential instructions to remain visible at all times
**Source:** [NN/G Placeholders Harmful](https://www.nngroup.com/articles/form-design-placeholders/)

### Pitfall 4: Help Link Tab-Jacking Vulnerability
**What goes wrong:** Using just target="_blank" allows opened page to access window.opener
**Why it happens:** Incomplete understanding of window.open security model
**How to avoid:** Always pair target="_blank" with rel="noopener noreferrer"
**Warning signs:** Security audits flag external link vulnerabilities
**Example:**
```vue
<!-- WRONG -->
<a :href="helpUrl" target="_blank">Help</a>

<!-- CORRECT -->
<a :href="helpUrl" target="_blank" rel="noopener noreferrer">Help</a>
```

### Pitfall 5: Hint Length Overflowing Form Layout
**What goes wrong:** 300+ character hints create massive whitespace below fields
**Why it happens:** No truncation logic, persistent-hint shows full text
**How to avoid:** Implement truncation at ~100 characters with show more/less toggle
**Warning signs:** Forms with excessive vertical spacing, poor mobile UX
**Recommendation:** Use Vuetify details slot for custom hint rendering with truncation

### Pitfall 6: Tooltip Delay Too Short or Missing
**What goes wrong:** Tooltips appear instantly on mouse movement, creating visual noise
**Why it happens:** Default open-delay in Vuetify is 0ms
**How to avoid:** Always set open-delay between 200-300ms (250ms recommended)
**Warning signs:** Users complain about distracting tooltips during mouse navigation
**Example:**
```vue
<v-tooltip :open-delay="250">
  <!-- activator and content -->
</v-tooltip>
```
**Source:** [Vuetify Tooltip API](https://vuetifyjs.com/en/components/tooltips/)

## Code Examples

Verified patterns from official sources and project context:

### Complete DynamicField Metadata Integration
```vue
<template>
  <div class="dynamic-field">
    <!-- Text Field with Full Metadata -->
    <v-text-field
      v-if="fieldSchema.type === 'string'"
      :model-value="modelValue"
      :label="getFieldLabel()"
      :placeholder="fieldSchema.placeholder"
      :variant="variant"
      :rules="getValidationRules()"
      :error-messages="getErrorMessages()"
      :required="fieldSchema.required"
      :disabled="disabled"
      :hint="getHintText()"
      :persistent-hint="!!fieldSchema.hint"
      @update:model-value="updateValue"
      @blur="handleBlur"
    >
      <!-- Prepend Icon with Tooltip -->
      <template v-if="hasMetadata" v-slot:prepend-inner>
        <v-tooltip
          location="top"
          :open-delay="250"
          :disabled="!fieldSchema.tooltip"
        >
          <template v-slot:activator="{ props }">
            <v-icon
              v-bind="props"
              :icon="fieldSchema.icon || 'mdi-information-outline'"
              color="grey-darken-1"
              size="small"
            />
          </template>
          <span>{{ fieldSchema.tooltip }}</span>
        </v-tooltip>
      </template>

      <!-- Help Link -->
      <template v-if="fieldSchema.helpUrl" v-slot:append-inner>
        <v-tooltip location="top" text="View documentation" :open-delay="250">
          <template v-slot:activator="{ props }">
            <v-icon
              v-bind="props"
              icon="mdi-help-circle-outline"
              color="primary"
              size="small"
              @click.stop="openHelpUrl"
              style="cursor: pointer;"
            />
          </template>
        </v-tooltip>
      </template>

      <!-- Custom Hint with Truncation (if needed) -->
      <template v-if="needsHintTruncation" v-slot:details>
        <div class="text-caption text-medium-emphasis">
          <span v-if="!hintExpanded">
            {{ truncatedHint }}
            <a @click.prevent="hintExpanded = true" class="text-primary ml-1">
              show more
            </a>
          </span>
          <span v-else>
            {{ fieldSchema.hint }}
            <a @click.prevent="hintExpanded = false" class="text-primary ml-1">
              show less
            </a>
          </span>
        </div>
      </template>
    </v-text-field>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()

const HINT_TRUNCATE_LENGTH = 100

const props = defineProps({
  fieldName: { type: String, required: true },
  fieldSchema: { type: Object, required: true },
  modelValue: { type: [String, Number, Boolean, Array, Object], default: null },
  variant: { type: String, default: 'filled' },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:model-value', 'validate'])

const hintExpanded = ref(false)

const hasMetadata = computed(() =>
  fieldSchema.icon || fieldSchema.tooltip
)

const needsHintTruncation = computed(() =>
  fieldSchema.hint && fieldSchema.hint.length > HINT_TRUNCATE_LENGTH
)

const truncatedHint = computed(() =>
  needsHintTruncation.value
    ? fieldSchema.hint.substring(0, HINT_TRUNCATE_LENGTH) + '...'
    : fieldSchema.hint
)

const getHintText = () => {
  // Only use default hint prop if not using custom truncation
  return needsHintTruncation.value ? undefined : fieldSchema.hint
}

const getFieldLabel = () => {
  return (
    props.fieldSchema.title ||
    props.fieldSchema.label ||
    props.fieldName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  )
}

const openHelpUrl = () => {
  if (!props.fieldSchema.helpUrl) {
    logger.warn('Help URL not defined', { fieldName: props.fieldName })
    return
  }

  window.open(props.fieldSchema.helpUrl, '_blank', 'noopener,noreferrer')

  logger.info('Help documentation opened', {
    fieldName: props.fieldName,
    helpUrl: props.fieldSchema.helpUrl
  })
}

const updateValue = (value) => {
  emit('update:model-value', value)
}

const handleBlur = (event) => {
  emit('validate', event.target.value)
}

// Validation and error methods from existing DynamicField.vue
const getValidationRules = () => {
  const rules = []
  if (props.fieldSchema.required) {
    rules.push(value => {
      if (value === null || value === undefined || value === '') {
        return `${getFieldLabel()} is required`
      }
      return true
    })
  }
  return rules
}

const getErrorMessages = () => {
  // Integration with validationResult prop from Phase 4
  return []
}
</script>

<style scoped>
.dynamic-field {
  width: 100%;
}
</style>
```
**Source:** Synthesized from project's existing DynamicField.vue and Vuetify 3 patterns

### Metadata Schema Mapping
```typescript
// Example field_definitions with metadata (from database schema)
const fieldDefinitions = {
  "proband_label": {
    "type": "string",
    "label": "Proband Identifier",
    "required": true,
    "min_length": 1,
    "icon": "mdi-account-box",
    "hint": "Unique identifier for the proband case. Use format: FAMILY_ID-PROBAND_NUMBER (e.g., FAM001-01)",
    "tooltip": "A proband is the individual in a family who brings the family to medical attention",
    "helpUrl": "https://www.clinicalgenome.org/docs/proband-definition"
  },
  "variant": {
    "type": "string",
    "label": "Variant",
    "required": true,
    "icon": "mdi-dna",
    "hint": "HGVS notation (e.g., c.123G>A, p.Arg41His)",
    "tooltip": "Use standard HGVS nomenclature for variant description",
    "helpUrl": "https://varnomen.hgvs.org/"
  }
}
```
**Source:** Project database schema pattern from 020_complete_sop11_schema.sql

### Conditional Metadata Rendering
```vue
<script setup>
// Only show icon if icon OR tooltip defined (show default icon if tooltip exists)
const shouldShowIcon = computed(() =>
  props.fieldSchema.icon || props.fieldSchema.tooltip
)

const iconName = computed(() =>
  props.fieldSchema.icon || 'mdi-information-outline'
)

// Gracefully handle missing metadata
const hasHint = computed(() =>
  props.fieldSchema.hint && props.fieldSchema.hint.trim().length > 0
)

const hasTooltip = computed(() =>
  props.fieldSchema.tooltip && props.fieldSchema.tooltip.trim().length > 0
)

const hasHelpUrl = computed(() =>
  props.fieldSchema.helpUrl &&
  (props.fieldSchema.helpUrl.startsWith('http://') ||
   props.fieldSchema.helpUrl.startsWith('https://'))
)
</script>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vuetify 2 tooltip activator `{ on }` | Vuetify 3 activator `{ props }` | Vuetify 3.0 (2022) | Breaking change, requires v-bind="props" |
| Placeholder-based hints | Persistent hints with persistent-hint prop | WCAG 2.1 adoption (~2019) | Accessibility requirement |
| `help_text` property | `hint` property (standardization) | Project convention | Aligns with Vuetify prop naming |
| Light gray icons (aesthetic) | Dark gray icons (WCAG compliant) | WCAG 2.1 AA requirement | 4.5:1 contrast ratio mandatory |
| Description field below form | Persistent hint integrated in field | Modern form UX (~2020+) | Better contextual guidance |

**Deprecated/outdated:**
- **description property:** Legacy approach, use hint instead (hint integrates with Vuetify persistent-hint)
- **Vuetify 2 { on } pattern:** Replaced by { props } in Vuetify 3
- **Icon-only indicators without text:** WCAG requires text alternatives for meaningful icons
- **Placeholder as primary instruction:** Violates WCAG 2.1, use persistent-hint

## Open Questions

Things that couldn't be fully resolved:

1. **Hint Formatting Support (Markdown vs Plain Text)**
   - What we know: Current schema uses plain text hints via help_text property
   - What's unclear: Whether hints should support markdown for rich formatting (bold, links, lists)
   - Recommendation: Start with plain text (simpler, safer), evaluate markdown need after user feedback. If needed, use vue3-markdown-it with sanitization

2. **Default Icon Behavior**
   - What we know: User decision shows default icon (mdi-information-outline) when tooltip defined but no icon specified
   - What's unclear: Should default icon show when ONLY hint is defined (no tooltip)?
   - Recommendation: Only show default icon when tooltip is defined (icon is tooltip trigger). Hints don't need icon decoration

3. **Mobile Touch Tooltip Behavior**
   - What we know: Tooltips are hover-based, mobile has no hover state
   - What's unclear: How tooltips should activate on mobile (tap? long-press? always visible?)
   - Recommendation: Vuetify v-tooltip handles mobile automatically (tap to show), verify in testing. Consider making tooltip content available in hint on mobile

4. **Help Link Icon Position on Mobile**
   - What we know: append-inner slot may cause layout issues on narrow screens
   - What's unclear: Whether help icon should move to different position on mobile
   - Recommendation: Keep append-inner, Vuetify handles responsive field sizing. Monitor mobile testing for usability issues

5. **Interaction Between Multiple Metadata Types**
   - What we know: Field can have icon + tooltip + hint + help link simultaneously
   - What's unclear: Best UX when all four are present (is it overwhelming?)
   - Recommendation: Allow all combinations, let real usage patterns emerge. Most fields won't use all four

## Sources

### Primary (HIGH confidence)
- [Vuetify 3 Text Fields Documentation](https://vuetifyjs.com/en/components/text-fields/) - Official API reference
- [Vuetify 3 Tooltips Documentation](https://vuetifyjs.com/en/components/tooltips/) - Official tooltip patterns
- [Vuetify GitHub - persistent-hint example](https://github.com/vuetifyjs/vuetify/blob/master/packages/docs/src/examples/v-text-field/prop-hint.vue) - Official code example
- [WCAG 2.1 Contrast Requirements](https://webaim.org/articles/contrast/) - WebAIM accessibility standards
- [NN/G: Placeholders Harmful](https://www.nngroup.com/articles/form-design-placeholders/) - Nielsen Norman Group research

### Secondary (MEDIUM confidence)
- [Form UX Best Practices 2026](https://www.designstudiouiux.com/blog/form-ux-design-best-practices/) - Persistent hints recommendation
- [UX West: External Links New Tabs](https://uxwest.com/when-why-how-website-links-should-open-new-tabs/) - Help link UX guidance
- [Smart Interface Design: Should Links Open New Tabs](https://smart-interface-design-patterns.com/articles/should-links-open-new-tabs/) - Workflow preservation rationale
- [WebAIM: Form Instructions](https://www.w3.org/WAI/tutorials/forms/instructions/) - W3C accessibility patterns
- [NN/G: Opening Links in New Windows](https://www.nngroup.com/articles/new-browser-windows-and-tabs/) - External link best practices

### Tertiary (LOW confidence)
- [CodePen: Vuetify Text Field Tooltip](https://codepen.io/scp-nm/pen/NWKgKvL) - Community example, unverified
- [vue-truncate-read-more](https://github.com/EranGrin/vue-read-more-truncate) - Library recommendation, not yet tested
- [Material Design Icons Library](https://pictogrammers.com/library/mdi/) - Icon reference, no metadata standards found
- WebSearch results on tooltip delays - No official Vuetify guidance found, 200-300ms is UX convention

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Vuetify 3 is project standard, patterns verified in official docs
- Architecture patterns: MEDIUM - Slot composition verified in docs, specific examples synthesized
- Icon contrast accessibility: HIGH - WCAG standards are authoritative
- Persistent hints: HIGH - W3C and NN/G research confirms best practice
- Help link behavior: MEDIUM - UX research consensus, but no single authoritative source
- Tooltip delays: LOW - No official Vuetify guidance, based on general UX convention
- Truncation implementation: LOW - Library found but not tested in project context

**Research date:** 2026-01-22
**Valid until:** 2026-02-21 (30 days - stable domain, Vuetify 3 API is mature)
