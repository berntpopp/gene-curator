#!/bin/bash
#
# UI/UX Review Quality Gate for Gene Curator
#
# This Stop hook blocks completion until a full UI/UX review is performed
# using Playwright MCP and documented in a report.
#
# Exit Codes:
#   0 - Output JSON response (approve or block)
#   2 - Block with stderr message (simpler but less control)
#
# JSON Response Fields:
#   decision: "approve" | "block"
#   reason: Instructions for Claude when blocking
#   systemMessage: Message shown to user

set -e

# Configuration
REPORT_DIR="plan/enhancements/tracking"
REVIEW_REPORT="${REPORT_DIR}/UI-UX-REVIEW-REPORT.md"
MIN_UI_SCORE=8
MIN_UX_SCORE=8
MIN_PLAN_SCORE=8

# Read stdin for hook context
HOOK_INPUT=$(cat)
STOP_HOOK_ACTIVE=$(echo "$HOOK_INPUT" | grep -o '"stop_hook_active":\s*true' || echo "")

# Function to output JSON safely (escapes newlines)
output_json() {
    local decision="$1"
    local reason="$2"
    local system_msg="$3"

    # Escape special characters for JSON
    reason=$(echo "$reason" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g' | sed 's/\t/\\t/g')

    printf '{"decision":"%s","reason":"%s","systemMessage":"%s"}\n' "$decision" "$reason" "$system_msg"
}

# If stop hook already forced continuation, check if review was completed
if [ -n "$STOP_HOOK_ACTIVE" ]; then
    # Check if a recent review report exists (within last hour)
    if [ -f "$REVIEW_REPORT" ]; then
        REPORT_AGE=$(( $(date +%s) - $(stat -c %Y "$REVIEW_REPORT" 2>/dev/null || echo "0") ))

        if [ "$REPORT_AGE" -lt 3600 ]; then
            # Parse scores from report
            UI_SCORE=$(grep -oP "UI Score:\s*\K\d+" "$REVIEW_REPORT" 2>/dev/null || echo "0")
            UX_SCORE=$(grep -oP "UX Score:\s*\K\d+" "$REVIEW_REPORT" 2>/dev/null || echo "0")
            PLAN_SCORE=$(grep -oP "Plan Implementation Score:\s*\K\d+" "$REVIEW_REPORT" 2>/dev/null || echo "0")

            # Check if all scores meet minimum
            if [ "$UI_SCORE" -ge "$MIN_UI_SCORE" ] && \
               [ "$UX_SCORE" -ge "$MIN_UX_SCORE" ] && \
               [ "$PLAN_SCORE" -ge "$MIN_PLAN_SCORE" ]; then
                output_json "approve" \
                    "UI/UX Review completed successfully. UI: ${UI_SCORE}/10, UX: ${UX_SCORE}/10, Plan: ${PLAN_SCORE}/10" \
                    "Quality gate passed: All scores >= 8/10"
                exit 0
            else
                # Scores below threshold - need iteration
                REASON="UI/UX Review scores below threshold. Current: UI=${UI_SCORE}/10, UX=${UX_SCORE}/10, Plan=${PLAN_SCORE}/10. Required: >= 8/10 each.

ITERATION REQUIRED:
1. Read the review report at ${REVIEW_REPORT}
2. Identify specific issues that lowered scores
3. Update plan/enhancements/tracking/014-PRECURATION-WORKFLOW-IMPLEMENTATION.md with fixes
4. Implement the highest-priority fixes
5. Run the UI/UX review again using Playwright MCP
6. Update the report with new scores

Focus on the lowest-scoring area first."
                output_json "block" "$REASON" "Quality gate: Scores below 8/10 threshold - iteration required"
                exit 0
            fi
        fi
    fi
fi

# No recent review - require one
REASON="STOP HOOK TRIGGERED: Full UI/UX Review Required

Before completing, you MUST perform a comprehensive UI/UX review using Playwright MCP.

## Review Checklist

### 1. Start Services (if not running)
Run: make hybrid-up && make backend (in background) && make frontend (in background)

### 2. Navigate to Application
Use browser_navigate to go to http://localhost:5193

### 3. Login
- Use credentials: admin@gene-curator.dev / admin123
- Verify login succeeds

### 4. Test Complete Workflow
Use Playwright MCP tools (browser_snapshot, browser_click, browser_type, browser_fill_form) to:

a) Create New Scope - Navigate to Scopes, click Add Scope, fill details, save
b) Add Genes to Scope - Search and add at least 3 genes (BRCA1, TP53, SCN1A)
c) Assign Curators - Navigate to scope settings, assign curator role
d) Curate a Gene - If curation UI exists, start curation, fill fields, test auto-save

### 5. Write Review Report
Create file: ${REVIEW_REPORT}

Include sections: Executive Summary, Test Results (PASS/FAIL for each step), UI Issues Found, UX Issues Found, Scores (UI Score: X/10, UX Score: X/10, Plan Implementation Score: X/10), Recommendations, Plan Updates Required

### 6. Score Criteria
- UI Score: Visual design, consistency, responsiveness, error states, loading states
- UX Score: Intuitiveness, workflow efficiency, feedback, discoverability, accessibility
- Plan Implementation Score: Features match plan, no missing functionality, proper error handling

### 7. Iterate if Needed
If any score < 8/10: Update the implementation plan with fixes, implement critical fixes, re-run review.

Only after ALL scores >= 8/10 can you complete."

output_json "block" "$REASON" "QUALITY GATE: UI/UX Review required before completion"
exit 0
