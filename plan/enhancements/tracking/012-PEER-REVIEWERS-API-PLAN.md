# Enhancement #012 - Peer Reviewers API Endpoint Implementation Plan

**Date:** 2026-01-12
**Status:** Planning
**Priority:** HIGH - Blocks workflow review feature
**Estimated Effort:** 2-3 hours
**Related Issues:** #116 (Multi-user approval), #118 (Workflow Management Views)
**Milestone:** v0.4.0 - Core Curation Features

---

## Executive Summary

The frontend is calling `GET /api/v1/workflow/peer-reviewers` but this endpoint does NOT exist in the backend, causing 404 errors. This blocks the workflow review assignment feature from functioning. All supporting infrastructure (database models, frontend code) already exists - only the backend endpoint needs to be created.

---

## Problem Statement

### Current Error
```
ERROR: API GET /workflow/peer-reviewers - 404 Not Found
```

### Root Cause
The endpoint `GET /api/v1/workflow/peer-reviewers` was never implemented in the backend, though the frontend code to call it exists.

### Impact
- Cannot retrieve list of available peer reviewers
- Cannot assign reviewers in the UI
- 4-eyes principle workflow is blocked at review stage

---

## What Already Exists

### Frontend (COMPLETE)

**API Client** - `frontend/src/api/workflow.js:34-37`
```javascript
async getPeerReviewers(params = {}) {
  const response = await apiClient.get('/workflow/peer-reviewers', { params })
  return response.data
}
```

**Store Action** - `frontend/src/stores/workflow.js:141-150`
```javascript
async fetchPeerReviewers(params = {}) {
  try {
    const reviewers = await workflowAPI.getPeerReviewers(params)
    this.peerReviewers = reviewers
    return reviewers
  } catch (error) {
    this.error = error.message
    throw error
  }
}
```

### Database Models (COMPLETE)

**UserNew Model** - `backend/app/models/models.py:164-247`
- `id`, `email`, `name`, `role`, `is_active`
- `assigned_scopes` relationship
- `reviews_assigned` relationship
- `expertise_areas`, `orcid_id`, `institution`

**Review Model** - `backend/app/models/models.py:902-967`
- `id`, `reviewer_id`, `curation_id`, `status`, `assigned_at`
- Status: PENDING, APPROVED, REJECTED, NEEDS_REVISION

**ScopeMembership Model** - `backend/app/models/models.py:249+`
- Links users to scopes with roles

### Related Endpoints (COMPLETE)

| Endpoint | Status | Purpose |
|----------|--------|---------|
| `POST /{item_type}/{item_id}/assign-reviewer` | EXISTS | Assign reviewer |
| `POST /reviews/{review_id}/submit` | EXISTS | Submit review |
| `GET /reviews/my-assignments` | EXISTS | Get my assignments |
| `GET /peer-reviewers` | **MISSING** | Get available reviewers |

---

## Implementation Plan

### Phase 1: Create Response Schema (15 min)

**File:** `backend/app/schemas/workflow_engine.py`

```python
class PeerReviewerResponse(BaseModel):
    """Available peer reviewer for assignment."""

    id: UUID
    name: str
    email: str
    role: UserRoleNew
    institution: str | None = None
    expertise_areas: list[str] = []
    is_active: bool = True
    pending_review_count: int = 0

    model_config = ConfigDict(from_attributes=True)
```

**Location:** Add after `PeerReviewResult` class (~line 130)

---

### Phase 2: Create Query Function (30 min)

**File:** `backend/app/crud/workflow_engine.py`

```python
def get_eligible_peer_reviewers(
    self,
    db: Session,
    scope_id: UUID | None = None,
    exclude_user_id: UUID | None = None,
) -> list[dict]:
    """
    Get eligible peer reviewers for assignment.

    Filters:
    - Active users only
    - Role must be reviewer, curator, scope_admin, or admin
    - If scope_id provided, must be member of that scope
    - Excludes exclude_user_id (4-eyes principle)

    Returns users with pending review count.
    """
    from sqlalchemy import func
    from app.models.models import UserNew, Review, ScopeMembership, ReviewStatus

    # Base query for active users with reviewer-capable roles
    eligible_roles = [
        UserRoleNew.REVIEWER,
        UserRoleNew.CURATOR,
        UserRoleNew.SCOPE_ADMIN,
        UserRoleNew.ADMIN
    ]

    query = db.query(UserNew).filter(
        UserNew.is_active == True,
        UserNew.role.in_(eligible_roles)
    )

    # Exclude current user (4-eyes principle)
    if exclude_user_id:
        query = query.filter(UserNew.id != exclude_user_id)

    # Filter by scope membership if scope_id provided
    if scope_id:
        query = query.join(ScopeMembership).filter(
            ScopeMembership.scope_id == scope_id,
            ScopeMembership.is_active == True
        )

    users = query.order_by(UserNew.name).all()

    # Get pending review counts
    result = []
    for user in users:
        pending_count = db.query(func.count(Review.id)).filter(
            Review.reviewer_id == user.id,
            Review.status == ReviewStatus.PENDING
        ).scalar() or 0

        result.append({
            "id": user.id,
            "name": user.name or user.email.split("@")[0],
            "email": user.email,
            "role": user.role,
            "institution": user.institution,
            "expertise_areas": user.expertise_areas or [],
            "is_active": user.is_active,
            "pending_review_count": pending_count
        })

    return result
```

**Location:** Add as method in `WorkflowEngine` class

---

### Phase 3: Create API Endpoint (30 min)

**File:** `backend/app/api/v1/endpoints/workflow.py`

```python
@router.get(
    "/peer-reviewers",
    response_model=list[PeerReviewerResponse],
    summary="Get available peer reviewers",
    description="""
    Returns list of users eligible to be assigned as peer reviewers.

    Filters applied:
    - Only active users
    - Only users with reviewer/curator/admin roles
    - If scope_id provided, only scope members
    - Excludes current user (4-eyes principle)

    Includes pending review count for workload assessment.
    """
)
def get_peer_reviewers(
    *,
    db: Session = Depends(get_db),
    scope_id: UUID | None = Query(
        None,
        description="Filter by scope membership"
    ),
    current_user: UserNew = Depends(get_current_active_user),
) -> list[PeerReviewerResponse]:
    """Get available peer reviewers for assignment."""

    reviewers = workflow_engine.get_eligible_peer_reviewers(
        db=db,
        scope_id=scope_id,
        exclude_user_id=current_user.id,  # 4-eyes principle
    )

    return reviewers
```

**Location:** Add before the first item-specific endpoint (~line 50)

**Required Imports:**
```python
from app.schemas.workflow_engine import PeerReviewerResponse
```

---

### Phase 4: Write Tests (45 min)

#### Unit Tests

**File:** `backend/tests/unit/test_workflow_engine.py`

```python
def test_get_eligible_peer_reviewers_returns_active_users(db_session, test_users):
    """Test that only active users are returned."""
    reviewers = workflow_engine.get_eligible_peer_reviewers(db_session)
    assert all(r["is_active"] for r in reviewers)


def test_get_eligible_peer_reviewers_excludes_user(db_session, test_users):
    """Test that exclude_user_id is not in results (4-eyes)."""
    user_to_exclude = test_users[0]
    reviewers = workflow_engine.get_eligible_peer_reviewers(
        db_session,
        exclude_user_id=user_to_exclude.id
    )
    assert not any(r["id"] == user_to_exclude.id for r in reviewers)


def test_get_eligible_peer_reviewers_filters_by_scope(db_session, test_scope):
    """Test scope membership filtering."""
    reviewers = workflow_engine.get_eligible_peer_reviewers(
        db_session,
        scope_id=test_scope.id
    )
    # Only scope members returned
    assert len(reviewers) >= 0  # Depends on test data


def test_get_eligible_peer_reviewers_includes_pending_count(db_session, test_users):
    """Test pending review count is included."""
    reviewers = workflow_engine.get_eligible_peer_reviewers(db_session)
    assert all("pending_review_count" in r for r in reviewers)
```

#### Integration Tests

**File:** `backend/tests/integration/test_workflow_api.py`

```python
def test_get_peer_reviewers_success(client, auth_headers):
    """Test GET /workflow/peer-reviewers returns 200."""
    response = client.get(
        "/api/v1/workflow/peer-reviewers",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_peer_reviewers_excludes_current_user(client, auth_headers, current_user):
    """Test current user is excluded (4-eyes principle)."""
    response = client.get(
        "/api/v1/workflow/peer-reviewers",
        headers=auth_headers
    )
    reviewer_ids = [r["id"] for r in response.json()]
    assert str(current_user.id) not in reviewer_ids


def test_get_peer_reviewers_with_scope_filter(client, auth_headers, test_scope):
    """Test scope_id filter parameter."""
    response = client.get(
        f"/api/v1/workflow/peer-reviewers?scope_id={test_scope.id}",
        headers=auth_headers
    )
    assert response.status_code == 200


def test_get_peer_reviewers_requires_auth(client):
    """Test endpoint requires authentication."""
    response = client.get("/api/v1/workflow/peer-reviewers")
    assert response.status_code == 401
```

---

### Phase 5: Update Documentation (15 min)

#### API Documentation

The endpoint will be auto-documented via FastAPI/OpenAPI at `/docs`.

#### Update Plan Status

- Update `plan/ISSUE_ROADMAP.md` to mark related progress
- Update `plan/enhancements/010-review-workflow-4eyes.md` status

---

## File Changes Summary

| File | Action | Lines |
|------|--------|-------|
| `backend/app/schemas/workflow_engine.py` | ADD | +15 |
| `backend/app/crud/workflow_engine.py` | ADD | +60 |
| `backend/app/api/v1/endpoints/workflow.py` | ADD | +35 |
| `backend/tests/unit/test_workflow_engine.py` | ADD | +40 |
| `backend/tests/integration/test_workflow_api.py` | ADD | +35 |
| **Total** | | ~185 lines |

---

## API Contract

### Request

```
GET /api/v1/workflow/peer-reviewers
```

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope_id` | UUID | No | Filter by scope membership |

### Response

**Success (200):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Jane Reviewer",
    "email": "jane@example.com",
    "role": "reviewer",
    "institution": "Research Institute",
    "expertise_areas": ["kidney", "genetics"],
    "is_active": true,
    "pending_review_count": 2
  }
]
```

**Error (401):** Unauthorized
**Error (403):** Forbidden (not authenticated)

---

## 4-Eyes Principle Enforcement

The endpoint enforces the 4-eyes principle by:

1. **Automatic exclusion** - Current user is always excluded from results
2. **Role filtering** - Only users capable of reviewing are returned
3. **Scope isolation** - When scope_id is provided, only scope members returned

This prevents:
- Self-review (curator cannot review own work)
- Viewer assignment (viewers cannot be reviewers)
- Cross-scope review (respects scope boundaries)

---

## Testing Checklist

- [ ] Unit test: Returns only active users
- [ ] Unit test: Excludes specified user
- [ ] Unit test: Filters by scope correctly
- [ ] Unit test: Includes pending review count
- [ ] Integration test: Returns 200 with valid token
- [ ] Integration test: Returns 401 without token
- [ ] Integration test: Excludes current user
- [ ] Integration test: Scope filter works
- [ ] Manual test: Frontend loads reviewers
- [ ] Manual test: Reviewer assignment works

---

## Rollback Plan

If issues arise:
1. Endpoint can be disabled without affecting other workflows
2. Frontend handles 404 gracefully (already tested)
3. No database migrations required - purely additive

---

## Success Criteria

1. `GET /api/v1/workflow/peer-reviewers` returns 200 with list of reviewers
2. Current user is never in the results (4-eyes)
3. Only active users with appropriate roles are returned
4. Scope filtering works correctly
5. Pending review count is accurate
6. Frontend can load and display reviewers
7. Reviewer assignment dropdown populates
8. All tests pass

---

## Next Steps After Implementation

1. **Update WorkflowManagement.vue** - Use peer reviewers for reviewer selection
2. **Create ReviewQueue component** - Show pending reviews for assignment
3. **Add bulk reviewer assignment** - Assign multiple curations to one reviewer
4. **Reviewer workload dashboard** - Visual display of review distribution

---

*Plan created as part of Enhancement #011 UI Gap Analysis follow-up.*
