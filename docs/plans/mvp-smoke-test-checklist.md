# MVP Smoke Test Checklist

Manual verification paths for MVP release.

## 1. Happy Path
- [ ] Admin assigns gene to scope
- [ ] Curator starts precuration, fills form, submits
- [ ] Curator starts curation from precuration, fills evidence, submits for review
- [ ] Reviewer receives notification, reviews curation
- [ ] Reviewer approves curation
- [ ] Curation becomes active
- [ ] Curator receives "approved" notification

## 2. Revision Loop
- [ ] Curator submits curation for review
- [ ] Reviewer requests revision (with comments)
- [ ] Curator receives "revision requested" notification
- [ ] Curator edits curation, resubmits
- [ ] Reviewer approves on second review

## 3. Rejection
- [ ] Reviewer rejects curation
- [ ] Curator receives "rejected" notification
- [ ] Curation returns to curation stage

## 4. 4-Eyes Enforcement
- [ ] Curator submits own curation
- [ ] Same curator cannot approve their own curation (error shown)
- [ ] Different user can approve

## 5. Multi-Scope
- [ ] User has curator role in Scope A, viewer role in Scope B
- [ ] Can curate in Scope A
- [ ] Cannot curate in Scope B (read-only)

## 6. Admin Dialogs
- [ ] View assignment dialog shows gene details
- [ ] Edit assignment dialog saves priority/notes changes
- [ ] Reassign dialog transfers gene to different curator
- [ ] Workflow view dialog shows pair details
- [ ] Workflow edit dialog saves name/description changes

## 7. Notification Flow
- [ ] Review assignment creates notification for reviewer
- [ ] Approval creates notification for curator
- [ ] Rejection creates notification for curator
- [ ] Mark-as-read works for single notification
- [ ] Mark-all-as-read clears unread badge
- [ ] Badge count updates on page refresh
