---
phase: M1-security-review-workflow
plan: 03
type: execute
wave: 2
depends_on: ["M1-02"]
files_modified:
  - frontend/src/components/navigation/MainNavigation.vue
autonomous: false

must_haves:
  truths:
    - "Review notification badge shows pending count on Review Queue nav item"
    - "Badge auto-refreshes every 60 seconds"
    - "Badge only shows when user is authenticated"
    - "Interval is cleaned up on component unmount (no memory leaks)"
  artifacts:
    - path: "frontend/src/components/navigation/MainNavigation.vue"
      provides: "Review Queue badge with pending count and auto-refresh"
      contains: "pendingReviewCount"
  key_links:
    - from: "frontend/src/components/navigation/MainNavigation.vue"
      to: "useWorkflowStore().fetchPendingReviewCount()"
      via: "interval-based polling every 60s"
      pattern: "fetchPendingReviewCount"
    - from: "MainNavigation.vue BaseNavigationItem"
      to: "badge prop"
      via: "conditional badge prop on review-queue item"
      pattern: "badge.*pendingReviewCount"
---

<objective>
Wire the review notification badge into the navigation and verify the complete review workflow works end-to-end.

Purpose: Reviewers need a visual indicator showing how many curations are waiting for their review. The `BaseNavigationItem` already supports a `badge` prop, and Plan M1-02 added `fetchPendingReviewCount()` to the workflow store. This plan wires them together with a 60-second auto-refresh interval.

Output: Review Queue nav item shows pending review count badge. End-to-end review workflow verified.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/MVP-PLAN.md
@.planning/phases/M1-security-review-workflow/M1-RESEARCH.md
@.planning/phases/M1-security-review-workflow/M1-02-SUMMARY.md

Key source files:
@frontend/src/components/navigation/MainNavigation.vue
@frontend/src/components/navigation/BaseNavigationItem.vue (reference — has badge and badgeColor props)
@frontend/src/stores/workflow.js (reference — has fetchPendingReviewCount after M1-02)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Wire review notification badge to MainNavigation</name>
  <files>frontend/src/components/navigation/MainNavigation.vue</files>
  <action>
Modify `frontend/src/components/navigation/MainNavigation.vue` to add a pending review count badge on the Review Queue navigation item.

**Script setup changes:**

1. Add imports (after existing imports around line 70-74):
```javascript
import { ref, onMounted, onUnmounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
```

Note: `computed` is already imported (line 70). Add `ref`, `onMounted`, `onUnmounted` to the import from 'vue'. The existing file imports `computed` from 'vue' — extend that to include the lifecycle hooks and ref.

2. Add state and lifecycle logic (after the `const { can, isAuthenticated } = usePermissions()` line, around line 78):
```javascript
const workflowStore = useWorkflowStore()
const pendingReviewCount = ref(0)
let badgeRefreshInterval = null

async function refreshBadgeCount() {
  try {
    pendingReviewCount.value = await workflowStore.fetchPendingReviewCount()
  } catch {
    // Silent fail for badge refresh — don't break navigation
  }
}

onMounted(async () => {
  if (isAuthenticated.value) {
    await refreshBadgeCount()
    badgeRefreshInterval = setInterval(refreshBadgeCount, 60000)
  }
})

onUnmounted(() => {
  if (badgeRefreshInterval) {
    clearInterval(badgeRefreshInterval)
    badgeRefreshInterval = null
  }
})
```

3. Modify the `curationItems` computed to include the badge count. Currently (line 100-113) it maps items from the router. Update the map to add badge data:

```javascript
const curationItems = computed(() => {
  return router
    .getRoutes()
    .filter(route => route.meta?.showInDropdown === 'curation')
    .filter(route => hasAccess(route.meta))
    .map(route => ({
      name: route.name,
      to: { name: route.name },
      icon: route.meta.icon,
      label: route.meta.label || route.meta.title,
      order: route.meta.order || 999,
      badge: route.name === 'review-queue' && pendingReviewCount.value > 0
        ? pendingReviewCount.value
        : null,
      badgeColor: 'warning'
    }))
    .sort((a, b) => a.order - b.order)
})
```

**Template changes:**

4. Update the `BaseNavigationItem` in the curation dropdown (around lines 21-27) to pass the badge props:

```html
<BaseNavigationItem
  v-for="item in curationItems"
  :key="item.name"
  :to="item.to"
  :icon="item.icon"
  :label="item.label"
  :badge="item.badge"
  :badge-color="item.badgeColor"
/>
```

This adds `:badge="item.badge"` and `:badge-color="item.badgeColor"` props. The `BaseNavigationItem` already supports both these props (verified — `badge` prop on line 105, `badgeColor` prop on line 113 of BaseNavigationItem.vue).

NOTE: Use `useLogger` from `@/composables/useLogger` if adding any log statements (NOT console.log). However, for the badge refresh, silent failure is preferred — no logging needed.
  </action>
  <verify>
Run `cd /home/bernt-popp/development/gene-curator && make test-frontend` to confirm all frontend tests pass. Run `make lint-frontend` to confirm no lint issues. Verify:
- `grep -n "pendingReviewCount" frontend/src/components/navigation/MainNavigation.vue` shows ref and usage
- `grep -n "setInterval" frontend/src/components/navigation/MainNavigation.vue` shows 60000ms interval
- `grep -n "clearInterval" frontend/src/components/navigation/MainNavigation.vue` shows cleanup in onUnmounted
- `grep -n ":badge" frontend/src/components/navigation/MainNavigation.vue` shows badge prop passed to BaseNavigationItem
  </verify>
  <done>Review Queue nav item shows pending count badge. Badge refreshes every 60s. Interval cleaned up on unmount. Frontend tests pass, lint clean.</done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
Complete M1 review workflow: SQL injection fix (Plan 01), ReviewQueue status fix + workflow store (Plan 02), and notification badge (this plan). The full set of changes:

1. Gene search uses parameterized queries (no SQL injection)
2. ReviewQueue fetches curations with 'in_review' status
3. 4-eyes principle filter excludes user's own curations from review queue
4. Workflow store has fetchPendingReviewCount() for badge count
5. Navigation badge shows pending review count with 60s auto-refresh
6. CurationDetailView already has Approve/Request Changes buttons (pre-existing)
  </what-built>
  <how-to-verify>
Start the development environment:
```bash
make hybrid-up   # Start DB
make backend     # Terminal 1
make frontend    # Terminal 2
```

1. **Login** at http://localhost:5193 with admin@gene-curator.dev / admin123

2. **Review Queue** — Navigate to Curation > Review Queue
   - Verify it loads without errors
   - If there are curations in 'in_review' status, they should appear
   - Your own curations should NOT appear (4-eyes principle)

3. **Notification Badge** — Look at the Curation dropdown in the top navigation
   - The "Review Queue" item should show a badge count if there are pending reviews
   - If no curations are in review, badge should not appear (count is 0)

4. **Gene Search** — Navigate to any gene search functionality
   - Search for a gene symbol (e.g., "BRCA1")
   - Verify search returns results normally (no errors from the parameterized query fix)

5. **Review Actions** (if test data available with curations in review):
   - Click on a curation in review status
   - Verify Approve and Request Changes buttons appear (if not your own curation)
   - Verify clicking Approve shows confirmation dialog with score summary
   - Verify clicking Request Changes shows dialog requiring feedback text

6. **All tests pass**:
   ```bash
   make test         # Backend tests
   make test-frontend # Frontend tests
   ```
  </how-to-verify>
  <resume-signal>Type "approved" to complete Phase M1, or describe any issues found.</resume-signal>
</task>

</tasks>

<verification>
1. `make test` passes all backend tests
2. `make test-frontend` passes all frontend tests
3. `make lint` and `make lint-frontend` pass
4. ReviewQueue shows correct curations (in_review status, not user's own)
5. Badge visible on Review Queue nav item when pending reviews exist
6. Gene search works without SQL injection vulnerability
</verification>

<success_criteria>
- Review notification badge shows pending count on Review Queue nav item
- Badge auto-refreshes every 60 seconds without memory leaks
- All M1 success criteria met:
  1. Gene search uses parameterized queries (no SQL injection)
  2. ReviewQueue shows pending reviews for current user across scopes
  3. CurationReview displays evidence with score and verdict (pre-existing CurationDetailView)
  4. Approve/Request Changes work end-to-end (pre-existing CurationDetailView)
  5. 4-eyes principle enforced (backend enforcement + frontend UX filter)
  6. Review notification badge shows pending count
  7. All existing tests still pass
</success_criteria>

<output>
After completion, create `.planning/phases/M1-security-review-workflow/M1-03-SUMMARY.md`
</output>
