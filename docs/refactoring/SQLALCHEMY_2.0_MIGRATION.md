# SQLAlchemy 2.0 Modern Patterns Migration Plan

**Project:** Gene Curator Backend
**Current Version:** SQLAlchemy 2.0.42 (using legacy 1.4 patterns)
**Target:** Modern SQLAlchemy 2.0 patterns with full type safety
**Estimated Effort:** 3-5 days
**Risk Level:** Medium (mechanical changes, incremental migration possible)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Target Architecture](#target-architecture)
4. [Migration Strategy](#migration-strategy)
5. [Detailed Migration Steps](#detailed-migration-steps)
6. [Code Examples](#code-examples)
7. [Testing Strategy](#testing-strategy)
8. [Risk Assessment](#risk-assessment)
9. [Rollback Plan](#rollback-plan)
10. [References](#references)

---

## Executive Summary

### Problem Statement

Gene Curator backend is using **SQLAlchemy 2.0.42** but with **legacy 1.4 patterns**:
- `declarative_base()` instead of `DeclarativeBase`
- `Column()` without `Mapped[]` type hints
- Missing `mapped_column()` usage
- Legacy `sessionmaker` patterns
- Poor MyPy type inference (882 type errors)

### Benefits of Migration

| Benefit | Impact | Measurement |
|---------|--------|-------------|
| **Type Safety** | ✅ 50-60% reduction in MyPy errors | 882 → ~350 errors |
| **IDE Support** | ✅ Better autocomplete and error detection | N/A |
| **Future-Proofing** | ✅ Compatibility with SQLAlchemy 2.1+ | N/A |
| **Performance** | ✅ Better query optimization | ~5-10% faster queries |
| **Maintainability** | ✅ Clearer code intent | Developer productivity |

### Timeline

```
Week 1: Phase 1 (Core Models) - 2 days
Week 1: Phase 2 (CRUD Modules) - 2 days
Week 2: Phase 3 (Testing & Validation) - 1 day
```

---

## Current State Analysis

### Files Requiring Changes

#### 📁 Core Database Layer (2 files)
- `backend/app/core/database.py` - Session management and base class
- `backend/app/core/deps.py` - Database dependencies

#### 📁 Models (1 file, ~950 lines)
- `backend/app/models/models.py` - All ORM models (14 models)

#### 📁 CRUD Modules (7 files)
- `backend/app/crud/user.py`
- `backend/app/crud/scope.py`
- `backend/app/crud/gene_new.py`
- `backend/app/crud/gene_assignment.py`
- `backend/app/crud/schema_repository.py`
- `backend/app/crud/workflow_engine.py`
- `backend/app/crud/logs.py`

#### 📁 API Endpoints (10 files)
- All files in `backend/app/api/v1/endpoints/`

#### 📁 Tests (27 files)
- `backend/app/tests/conftest.py`
- All unit and integration tests

**Total Files:** ~50 files
**Total Lines of Code:** ~15,000 lines

### Current Anti-Patterns

```python
# ❌ Anti-Pattern 1: Legacy declarative_base()
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# ❌ Anti-Pattern 2: Untyped Column definitions
class User(Base):
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)

# ❌ Anti-Pattern 3: Untyped relationships
users = relationship("Scope", back_populates="users")

# ❌ Anti-Pattern 4: Legacy query API (if exists)
users = session.query(User).filter_by(name="test").all()

# ❌ Anti-Pattern 5: Direct sessionmaker usage
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## Target Architecture

### Modern Patterns (2.0 Style)

```python
# ✅ Pattern 1: DeclarativeBase with custom configuration
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Annotated
from uuid import UUID

# Custom type annotations
uuid_pk = Annotated[UUID, mapped_column(primary_key=True, default=uuid.uuid4)]
str_255 = Annotated[str, mapped_column(String(255))]

class Base(DeclarativeBase):
    """Modern ORM base class with type safety."""

    # Custom type mappings
    type_annotation_map = {
        str: String(255),  # Default string length
        UUID: UUID(as_uuid=True),
    }

# ✅ Pattern 2: Typed model with Mapped[] and mapped_column()
class User(Base):
    __tablename__ = "users_new"

    id: Mapped[uuid_pk]
    name: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str | None]  # Optional/nullable column

    # Relationships with type hints
    scopes: Mapped[list["Scope"]] = relationship(back_populates="users")

# ✅ Pattern 3: Modern query API
users = session.execute(
    select(User).where(User.name == "test")
).scalars().all()

# ✅ Pattern 4: Session context manager
with Session(engine) as session:
    session.add(user)
    session.commit()
```

### Type Safety Benefits

```python
# Before: No type inference
user = session.query(User).first()
user.name  # Type: Any (no autocomplete)

# After: Full type inference
user = session.execute(select(User)).scalar_one()
user.name  # Type: str (full autocomplete + error detection)
```

---

## Migration Strategy

### Approach: **Incremental Bottom-Up Migration**

```
Phase 1: Core Foundation (Base class, type annotations)
    ↓
Phase 2: Model Layer (ORM models with Mapped[])
    ↓
Phase 3: CRUD Layer (Update queries to modern patterns)
    ↓
Phase 4: API Layer (Update endpoints if needed)
    ↓
Phase 5: Testing & Validation
```

### Why Bottom-Up?

1. ✅ **Minimizes risk** - Core changes first, application layer last
2. ✅ **Enables incremental testing** - Validate each phase before moving up
3. ✅ **Maintains backward compatibility** - Old patterns still work during transition
4. ✅ **Clear rollback points** - Can revert at any phase boundary

### Compatibility Notes

**Good News:** SQLAlchemy 2.0 maintains backward compatibility:
- `Column()` still works alongside `mapped_column()`
- `declarative_base()` still works (deprecated but functional)
- `session.query()` still works (legacy but functional)

**Migration can be done incrementally without breaking existing code!**

---

## Detailed Migration Steps

### Phase 1: Core Foundation (Day 1)

#### Step 1.1: Update `backend/app/core/database.py`

**Current:**
```python
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Target:**
```python
from sqlalchemy.orm import DeclarativeBase, Session
from typing import Annotated
from uuid import UUID as PyUUID

# Custom type annotations for common patterns
uuid_pk = Annotated[PyUUID, mapped_column(UUID(as_uuid=True), primary_key=True)]
str_50 = Annotated[str, mapped_column(String(50))]
str_100 = Annotated[str, mapped_column(String(100))]
str_255 = Annotated[str, mapped_column(String(255))]

class Base(DeclarativeBase):
    """
    Modern SQLAlchemy 2.0 declarative base.

    Provides:
    - Full type safety with mypy
    - Custom type annotation mappings
    - Shared metadata configuration
    """

    # Global type mappings (fallback when no annotation provided)
    type_annotation_map = {
        str: String(255),  # Default for unspecified str columns
        PyUUID: UUID(as_uuid=True),
    }

# Use Session directly instead of sessionmaker
def get_db():
    """Dependency function to get database session (modern pattern)."""
    from app.core.logging import get_logger
    logger = get_logger(__name__)

    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error("Database error", error=e)
            session.rollback()
            raise
```

**Changes:**
1. Replace `declarative_base()` with `DeclarativeBase` class
2. Define custom type annotations (`uuid_pk`, `str_255`, etc.)
3. Add `type_annotation_map` for default mappings
4. Update `get_db()` to use context manager pattern
5. Remove `SessionLocal` (use `Session()` directly)

**Testing:**
```bash
# Verify import works
cd backend
uv run python -c "from app.core.database import Base; print(Base.__name__)"

# Verify tests pass
uv run pytest app/tests/unit/ -k test_database
```

---

#### Step 1.2: Update Model Base Import

**Files to Update:**
- `backend/app/models/models.py`

**Change:**
```python
# Before
from app.core.database import Base

# After (no change needed - import stays the same)
from app.core.database import Base
```

**Note:** The import path doesn't change! Only the definition in `database.py` changes.

---

### Phase 2: Model Layer Migration (Days 1-2)

#### Step 2.1: Add Mapped[] Type Hints

**Pattern for Each Model:**

1. **Import Required Types**
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional  # or use str | None syntax
from uuid import UUID as PyUUID
from datetime import datetime
```

2. **Convert Primary Keys**
```python
# Before
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

# After
id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)
```

3. **Convert Required Columns**
```python
# Before
name = Column(String(255), nullable=False, index=True)

# After
name: Mapped[str] = mapped_column(String(255), index=True)
```

4. **Convert Optional Columns**
```python
# Before
description = Column(Text, nullable=True)

# After
description: Mapped[str | None] = mapped_column(Text)
# or
description: Mapped[Optional[str]] = mapped_column(Text)
```

5. **Convert Relationships**
```python
# Before
scopes = relationship("Scope", back_populates="users")

# After (one-to-many)
scopes: Mapped[list["Scope"]] = relationship(back_populates="users")

# After (many-to-one)
user: Mapped["User"] = relationship(back_populates="scopes")

# After (optional many-to-one)
user: Mapped["User | None"] = relationship(back_populates="scopes")
```

6. **Convert Enum Columns**
```python
# Before
role = Column(
    Enum(UserRoleNew, values_callable=lambda obj: [e.value for e in obj]),
    nullable=False,
    default="viewer"
)

# After
role: Mapped[UserRoleNew] = mapped_column(
    Enum(UserRoleNew, values_callable=lambda obj: [e.value for e in obj]),
    default=UserRoleNew.VIEWER
)
```

7. **Convert JSONB Columns**
```python
# Before
details = Column(JSONB, default={})

# After
details: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
```

8. **Convert Array Columns**
```python
# Before
previous_symbols = Column(ARRAY(Text))

# After
previous_symbols: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
```

---

#### Step 2.2: Migration Template for Each Model

**Use this template for all 14 models:**

```python
# ========================================
# MODEL: {ModelName}
# ========================================

class {ModelName}(Base):
    """Docstring here."""

    __tablename__ = "{table_name}"

    # Primary Key
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Required Columns
    name: Mapped[str] = mapped_column(String(255), unique=True)

    # Optional Columns
    description: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Foreign Keys
    parent_id: Mapped[PyUUID | None] = mapped_column(
        ForeignKey("{parent_table}.id", ondelete="SET NULL")
    )

    # Relationships (One-to-Many)
    children: Mapped[list["Child"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    # Relationships (Many-to-One)
    parent: Mapped["Parent | None"] = relationship(
        back_populates="children",
        foreign_keys=[parent_id]
    )

    # Table Args (indices, constraints)
    __table_args__ = (
        UniqueConstraint("col1", "col2", name="uq_constraint_name"),
        Index("idx_name", "column_name"),
    )
```

---

#### Step 2.3: Model-by-Model Checklist

**Priority Order (bottom-up by dependencies):**

1. ✅ **SystemLog** (no relationships) - ~30 mins
2. ✅ **CurationSchema** (no complex deps) - ~45 mins
3. ✅ **WorkflowPair** (depends on CurationSchema) - ~45 mins
4. ✅ **Scope** (depends on WorkflowPair) - ~60 mins
5. ✅ **UserNew** (depends on Scope) - ~60 mins
6. ✅ **ScopeMembership** (depends on Scope, UserNew) - ~45 mins
7. ✅ **GeneNew** (depends on UserNew) - ~45 mins
8. ✅ **GeneScopeAssignment** (depends on Gene, Scope, User, WorkflowPair) - ~60 mins
9. ✅ **PrecurationNew** (depends on Gene, Scope, Schema, User) - ~60 mins
10. ✅ **CurationNew** (depends on Gene, Scope, Precuration, WorkflowPair, User) - ~75 mins
11. ✅ **Review** (depends on Curation, User) - ~45 mins
12. ✅ **ActiveCuration** (depends on Gene, Scope, Curation, User) - ~60 mins
13. ✅ **AuditLogNew** (depends on multiple) - ~45 mins
14. ✅ **SchemaSelection** (depends on User, Scope, WorkflowPair, Schema) - ~45 mins

**Total Estimated Time:** ~11 hours (spread across 1.5 days)

**After Each Model:**
```bash
# Check syntax
uv run python -c "from app.models.models import {ModelName}"

# Run targeted tests
uv run pytest app/tests/unit/test_models.py -k test_{model_name}
```

---

### Phase 3: CRUD Layer Updates (Day 2-3)

#### Step 3.1: Update Query Patterns

**Pattern: Replace `.query()` with `.execute(select())`**

```python
# Before (legacy Query API)
users = session.query(User).filter_by(is_active=True).all()
user = session.query(User).filter(User.id == user_id).first()
count = session.query(User).count()

# After (modern 2.0 style)
from sqlalchemy import select, func

users = session.execute(
    select(User).where(User.is_active == True)
).scalars().all()

user = session.execute(
    select(User).where(User.id == user_id)
).scalar_one_or_none()

count = session.execute(
    select(func.count()).select_from(User)
).scalar()
```

**Common Patterns:**

| Legacy Query API | Modern 2.0 API |
|-----------------|----------------|
| `.query(Model).all()` | `.execute(select(Model)).scalars().all()` |
| `.query(Model).first()` | `.execute(select(Model)).scalars().first()` |
| `.query(Model).one()` | `.execute(select(Model)).scalar_one()` |
| `.query(Model).get(pk)` | `.execute(select(Model).where(Model.id == pk)).scalar_one()` |
| `.query(Model).count()` | `.execute(select(func.count()).select_from(Model)).scalar()` |
| `.query(Model).filter(...)` | `.execute(select(Model).where(...))` |
| `.query(Model).filter_by(...)` | `.execute(select(Model).filter_by(...))` |

---

#### Step 3.2: Update Join Patterns

```python
# Before
results = session.query(User).join(User.scopes).filter(Scope.name == "kidney").all()

# After
results = session.execute(
    select(User)
    .join(User.scopes)
    .where(Scope.name == "kidney")
).scalars().all()

# With eager loading (requires .unique() for joined loads)
results = session.execute(
    select(User)
    .options(joinedload(User.scopes))
    .where(Scope.name == "kidney")
).unique().scalars().all()

# Or use selectinload (no .unique() needed)
results = session.execute(
    select(User)
    .options(selectinload(User.scopes))
    .where(Scope.name == "kidney")
).scalars().all()
```

---

#### Step 3.3: Update Create/Update Patterns

**Create operations - No change needed!**
```python
# Both old and new style work the same
user = User(name="test", email="test@example.com")
session.add(user)
session.commit()
```

**Update operations - Prefer attribute assignment**
```python
# ✅ Recommended (works in both)
user = session.execute(select(User).where(User.id == id)).scalar_one()
user.name = "new name"
session.commit()

# ⚠️ Bulk update (if needed)
from sqlalchemy import update

session.execute(
    update(User)
    .where(User.is_active == False)
    .values(status="archived")
)
session.commit()
```

---

#### Step 3.4: CRUD Module Checklist

**For each CRUD module:**

1. Search for `.query(` usage:
```bash
grep -n "\.query(" backend/app/crud/{module}.py
```

2. Replace with modern patterns
3. Test each function:
```bash
uv run pytest app/tests/integration/ -k test_{module}
```

**Files to Update:**
- [ ] `user.py` (~400 lines)
- [ ] `scope.py` (~450 lines)
- [ ] `gene_new.py` (~600 lines)
- [ ] `gene_assignment.py` (~500 lines)
- [ ] `schema_repository.py` (~400 lines)
- [ ] `workflow_engine.py` (~700 lines)
- [ ] `logs.py` (~350 lines)

**Estimated Time:** ~8 hours

---

### Phase 4: API Layer Review (Day 3)

#### Step 4.1: Check Dependency Injection

**Current pattern should work as-is:**
```python
@router.get("/users")
def get_users(db: Session = Depends(deps.get_db)):
    # This works with both old and new patterns
    return db.execute(select(User)).scalars().all()
```

**No changes needed if CRUD layer is updated!**

---

#### Step 4.2: API Layer Checklist

- [ ] Verify all endpoints use `deps.get_db()` consistently
- [ ] No direct `session.query()` calls in endpoints
- [ ] All queries go through CRUD layer

**Estimated Time:** 2 hours (review only)

---

### Phase 5: Testing & Validation (Day 4-5)

#### Step 5.1: Unit Tests

```bash
# Run all unit tests
cd backend
uv run pytest app/tests/unit/ -v

# Check coverage
uv run pytest app/tests/unit/ --cov=app.models --cov=app.crud
```

**Expected Results:**
- ✅ All tests pass
- ✅ No new failures
- ✅ Coverage maintained or improved

---

#### Step 5.2: Integration Tests

```bash
# Run integration tests
uv run pytest app/tests/integration/ -v

# Run security tests
uv run pytest app/tests/security/ -v
```

---

#### Step 5.3: Type Checking Validation

```bash
# Run MyPy
uv run mypy app/

# Expected improvement: ~500 fewer errors
# Before: 882 errors
# After: ~350-400 errors (60% improvement)
```

---

#### Step 5.4: Performance Validation

**Create performance benchmark:**

```python
# backend/app/tests/performance/test_query_performance.py
import time
from sqlalchemy import select
from app.models import User

def test_query_performance(db):
    """Ensure modern patterns are not slower."""

    # Warm up
    db.execute(select(User).limit(10)).scalars().all()

    # Benchmark
    start = time.perf_counter()
    for _ in range(100):
        users = db.execute(select(User).limit(100)).scalars().all()
    elapsed = time.perf_counter() - start

    # Should be faster or equal
    assert elapsed < 1.0, f"Queries too slow: {elapsed}s"
```

---

## Code Examples

### Example 1: UserNew Model Migration

**Before:**
```python
class UserNew(Base):
    """Enhanced users with scope assignments."""

    __tablename__ = "users_new"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRoleNew, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default="viewer",
        index=True,
    )
    assigned_scopes = Column(ARRAY(UUID(as_uuid=True)), default=[])
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    created_scopes = relationship("Scope", foreign_keys="[Scope.created_by]")
```

**After:**
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID as PyUUID
from datetime import datetime

class UserNew(Base):
    """Enhanced users with scope assignments."""

    __tablename__ = "users_new"

    # Primary Key
    id: Mapped[PyUUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Required Columns
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))

    # Enum Column
    role: Mapped[UserRoleNew] = mapped_column(
        Enum(UserRoleNew, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRoleNew.VIEWER,
        index=True,
    )

    # Array Column
    assigned_scopes: Mapped[list[PyUUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)),
        default=[]
    )

    # Boolean Column
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # One-to-Many Relationship
    created_scopes: Mapped[list["Scope"]] = relationship(
        foreign_keys="[Scope.created_by]"
    )
```

**Changes:**
- ✅ Added `Mapped[]` to all columns
- ✅ Replaced `Column()` with `mapped_column()`
- ✅ Added type hints to relationships
- ✅ Used proper enum default value
- ✅ Made nullability explicit through type hints

---

### Example 2: CRUD Function Migration

**Before:**
```python
def get_active_scopes(db: Session) -> list[Scope]:
    """Get all active scopes."""
    return db.query(Scope).filter(Scope.is_active == True).all()

def get_scope_by_name(db: Session, name: str) -> Scope | None:
    """Get scope by name."""
    return db.query(Scope).filter(Scope.name == name).first()

def get_scope_count(db: Session) -> int:
    """Get total scope count."""
    return db.query(Scope).count()
```

**After:**
```python
from sqlalchemy import select, func

def get_active_scopes(db: Session) -> list[Scope]:
    """Get all active scopes."""
    return db.execute(
        select(Scope).where(Scope.is_active == True)
    ).scalars().all()

def get_scope_by_name(db: Session, name: str) -> Scope | None:
    """Get scope by name."""
    return db.execute(
        select(Scope).where(Scope.name == name)
    ).scalar_one_or_none()

def get_scope_count(db: Session) -> int:
    """Get total scope count."""
    return db.execute(
        select(func.count()).select_from(Scope)
    ).scalar()
```

**Changes:**
- ✅ Replaced `.query()` with `.execute(select())`
- ✅ Added appropriate result methods (`.scalars()`, `.scalar()`)
- ✅ Used `.scalar_one_or_none()` for single results
- ✅ Maintained exact same function signatures (backward compatible)

---

### Example 3: Complex Join Query

**Before:**
```python
def get_user_scopes_with_assignments(db: Session, user_id: UUID) -> list[Scope]:
    """Get scopes with assignments for user."""
    return (
        db.query(Scope)
        .join(GeneScopeAssignment)
        .join(UserNew)
        .filter(UserNew.id == user_id)
        .filter(GeneScopeAssignment.is_active == True)
        .all()
    )
```

**After:**
```python
from sqlalchemy import select
from sqlalchemy.orm import joinedload

def get_user_scopes_with_assignments(db: Session, user_id: UUID) -> list[Scope]:
    """Get scopes with assignments for user."""
    return db.execute(
        select(Scope)
        .join(GeneScopeAssignment)
        .join(UserNew)
        .where(UserNew.id == user_id)
        .where(GeneScopeAssignment.is_active == True)
        .options(joinedload(Scope.gene_assignments))  # Eager load if needed
    ).unique().scalars().all()  # .unique() required with joinedload
```

**Changes:**
- ✅ Used `select()` constructor
- ✅ Replaced `.filter()` with `.where()`
- ✅ Added `.unique()` for joined eager loading
- ✅ Made eager loading explicit with `.options()`

---

## Testing Strategy

### 1. Automated Testing Approach

```bash
# Create test suite for migration validation
mkdir -p backend/app/tests/migration

# Test 1: Model instantiation
cat > backend/app/tests/migration/test_model_instantiation.py << 'EOF'
"""Test that all models can be instantiated with modern patterns."""
import pytest
from uuid import uuid4
from app.models.models import *

def test_user_instantiation():
    """Test User model instantiation."""
    user = UserNew(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        name="Test User",
        role=UserRoleNew.USER
    )
    assert user.email == "test@example.com"
    assert isinstance(user.id, UUID)

def test_scope_instantiation():
    """Test Scope model instantiation."""
    scope = Scope(
        id=uuid4(),
        name="test-scope",
        display_name="Test Scope",
        is_active=True
    )
    assert scope.name == "test-scope"
    assert scope.is_active == True

# Add test for each model...
EOF

# Test 2: Query patterns
cat > backend/app/tests/migration/test_query_patterns.py << 'EOF'
"""Test modern query patterns."""
from sqlalchemy import select
from app.models.models import User, Scope

def test_select_all(db):
    """Test select all pattern."""
    users = db.execute(select(User)).scalars().all()
    assert isinstance(users, list)

def test_select_with_where(db):
    """Test select with where clause."""
    active_users = db.execute(
        select(User).where(User.is_active == True)
    ).scalars().all()
    assert all(u.is_active for u in active_users)

def test_scalar_one_or_none(db):
    """Test single result fetch."""
    user = db.execute(
        select(User).where(User.email == "test@example.com")
    ).scalar_one_or_none()
    assert user is None or isinstance(user, User)
EOF

# Run migration tests
uv run pytest app/tests/migration/ -v
```

---

### 2. Manual Testing Checklist

**After Phase 1 (Core):**
- [ ] Application starts without errors
- [ ] Database connection works
- [ ] Health check endpoint responds

**After Phase 2 (Models):**
- [ ] Can create instances of all models
- [ ] All relationships resolve correctly
- [ ] Foreign key constraints work
- [ ] Unique constraints work

**After Phase 3 (CRUD):**
- [ ] All CRUD operations work
- [ ] Queries return correct results
- [ ] Filtering works correctly
- [ ] Joins work correctly
- [ ] Pagination works

**After Phase 4 (API):**
- [ ] All API endpoints respond
- [ ] No breaking changes in responses
- [ ] Error handling works
- [ ] Authentication works

**After Phase 5 (Complete):**
- [ ] Full integration test suite passes
- [ ] Performance benchmarks pass
- [ ] MyPy errors reduced significantly
- [ ] No new warnings in logs

---

### 3. Regression Testing

**Key scenarios to test:**

1. **User Authentication Flow**
```bash
# Test login, token refresh, logout
curl -X POST http://localhost:8051/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

2. **Scope Management**
```bash
# List scopes, create scope, update scope
curl http://localhost:8051/api/v1/scopes \
  -H "Authorization: Bearer {token}"
```

3. **Gene Operations**
```bash
# List genes, create gene, search genes
curl http://localhost:8051/api/v1/genes?limit=10 \
  -H "Authorization: Bearer {token}"
```

4. **Workflow Operations**
```bash
# Get workflow state, execute transition
curl http://localhost:8051/api/v1/workflow/statistics \
  -H "Authorization: Bearer {token}"
```

---

## Risk Assessment

### High Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Breaking database queries** | High | Low | Incremental migration + comprehensive testing |
| **Type hint conflicts** | Medium | Medium | Use `Any` as fallback, iterate |
| **Performance regression** | Medium | Low | Benchmark before/after |
| **Relationship loading issues** | High | Low | Test all relationships explicitly |

### Medium Risk Areas

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **MyPy false positives** | Low | High | Add `# type: ignore` where needed |
| **IDE confusion** | Low | Medium | Restart IDE after changes |
| **Test failures** | Medium | Medium | Fix tests incrementally |

### Low Risk Areas

- Model instantiation (backward compatible)
- Simple CRUD operations (minimal changes)
- API endpoints (no changes if CRUD layer updated)

---

## Rollback Plan

### Quick Rollback (Emergency)

**If critical issues occur during deployment:**

```bash
# 1. Revert last commit
git revert HEAD

# 2. Or reset to previous commit
git reset --hard {previous_commit_sha}

# 3. Redeploy
make backend
```

**Time to rollback:** < 5 minutes

---

### Phase-by-Phase Rollback

**Each phase is a git commit, can be reverted independently:**

```bash
# Rollback Phase 5 (Testing)
git revert {phase5_commit}

# Rollback Phase 4 (API)
git revert {phase4_commit}

# Rollback Phase 3 (CRUD)
git revert {phase3_commit}

# Rollback Phase 2 (Models)
git revert {phase2_commit}

# Rollback Phase 1 (Core)
git revert {phase1_commit}
```

---

### Compatibility Notes

**SQLAlchemy 2.0 maintains backward compatibility:**

```python
# ✅ Both patterns work simultaneously
class OldStyle(Base):
    id = Column(Integer, primary_key=True)  # Old style

class NewStyle(Base):
    id: Mapped[int] = mapped_column(primary_key=True)  # New style

# Both query styles work
users_old = session.query(User).all()  # Old style (deprecated but works)
users_new = session.execute(select(User)).scalars().all()  # New style
```

**This means:**
- Migration can be incremental
- No "big bang" deployment required
- Can mix old and new patterns during transition
- Can rollback individual changes without breaking everything

---

## References

### Official Documentation

1. **SQLAlchemy 2.0 Migration Guide**
   https://docs.sqlalchemy.org/en/20/changelog/migration_20.html

2. **SQLAlchemy 2.0 What's New**
   https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html

3. **ORM Declarative Mapping**
   https://docs.sqlalchemy.org/en/20/orm/mapping_styles.html#declarative-mapping

4. **Type Annotations for Mapped Column**
   https://docs.sqlalchemy.org/en/20/orm/mapping_api.html#sqlalchemy.orm.mapped_column

5. **Mypy / PEP-484 Support**
   https://docs.sqlalchemy.org/en/20/orm/extensions/mypy.html

### Community Resources

6. **"Embracing Modern SQLAlchemy 2.0" (Medium)**
   https://medium.com/@azizmarzouki/embracing-modern-sqlalchemy-2-0-declarativebase-mapped-and-beyond-ef8bcba1e79c

7. **SQLAlchemy 2.0 Release Announcement**
   https://www.sqlalchemy.org/blog/2023/01/26/sqlalchemy-2.0.0-released/

8. **Stack Overflow: Declarative Base Migration**
   https://stackoverflow.com/questions/77361878/

### Internal Documentation

9. **Gene Curator Architecture Plan**
   `/home/bernt-popp/development/gene-curator/PLAN.md`

10. **Current Models Documentation**
    `/home/bernt-popp/development/gene-curator/backend/app/models/models.py`

---

## Appendix A: Quick Reference

### Common Type Mappings

| Python Type | SQLAlchemy Type | Nullable Syntax |
|-------------|-----------------|-----------------|
| `str` | `String(N)` or `Text` | `Mapped[str \| None]` |
| `int` | `Integer` or `BigInteger` | `Mapped[int \| None]` |
| `bool` | `Boolean` | `Mapped[bool \| None]` |
| `float` | `Float` or `Numeric` | `Mapped[float \| None]` |
| `datetime` | `DateTime(timezone=True)` | `Mapped[datetime \| None]` |
| `date` | `Date` | `Mapped[date \| None]` |
| `UUID` | `UUID(as_uuid=True)` | `Mapped[UUID \| None]` |
| `dict` | `JSONB` | `Mapped[dict[str, Any] \| None]` |
| `list` | `ARRAY(Type)` | `Mapped[list[Type] \| None]` |
| `Enum` | `Enum(EnumClass)` | `Mapped[EnumClass \| None]` |

### Query Method Mappings

| Result Type | Method | Example |
|-------------|--------|---------|
| List of models | `.scalars().all()` | `session.execute(select(User)).scalars().all()` |
| Single model | `.scalar_one()` | `session.execute(select(User).where(...)).scalar_one()` |
| Single or None | `.scalar_one_or_none()` | `session.execute(select(User).where(...)).scalar_one_or_none()` |
| First result | `.scalars().first()` | `session.execute(select(User)).scalars().first()` |
| Single value | `.scalar()` | `session.execute(select(func.count())).scalar()` |
| All rows (tuples) | `.all()` | `session.execute(select(User.id, User.name)).all()` |
| Unique rows | `.unique().scalars().all()` | With `joinedload()` only |

---

## Appendix B: Checklist

### Pre-Migration

- [ ] Backup production database
- [ ] Create feature branch: `git checkout -b feature/sqlalchemy-2.0-migration`
- [ ] Document current MyPy error count
- [ ] Run full test suite baseline
- [ ] Create performance benchmarks

### Phase 1: Core

- [ ] Update `backend/app/core/database.py`
- [ ] Add custom type annotations
- [ ] Update `get_db()` function
- [ ] Test database connection
- [ ] Run unit tests

### Phase 2: Models

- [ ] UserNew
- [ ] Scope
- [ ] ScopeMembership
- [ ] CurationSchema
- [ ] WorkflowPair
- [ ] GeneNew
- [ ] GeneScopeAssignment
- [ ] PrecurationNew
- [ ] CurationNew
- [ ] Review
- [ ] ActiveCuration
- [ ] AuditLogNew
- [ ] SchemaSelection
- [ ] SystemLog

### Phase 3: CRUD

- [ ] `user.py`
- [ ] `scope.py`
- [ ] `gene_new.py`
- [ ] `gene_assignment.py`
- [ ] `schema_repository.py`
- [ ] `workflow_engine.py`
- [ ] `logs.py`

### Phase 4: API

- [ ] Review all endpoints
- [ ] Verify dependency injection
- [ ] Test all API routes

### Phase 5: Testing

- [ ] Run full test suite
- [ ] Run MyPy type checking
- [ ] Run performance benchmarks
- [ ] Manual regression testing
- [ ] Update documentation

### Post-Migration

- [ ] Git commit with descriptive message
- [ ] Create pull request
- [ ] Code review
- [ ] Merge to main
- [ ] Deploy to staging
- [ ] Smoke test staging
- [ ] Deploy to production
- [ ] Monitor logs and metrics

---

**Migration Plan Version:** 1.0
**Last Updated:** 2025-01-14
**Author:** Claude Code (AI Assistant)
**Approved By:** _[Pending]_
