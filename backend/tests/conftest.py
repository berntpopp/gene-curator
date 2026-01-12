"""Pytest configuration and shared fixtures for Gene Curator tests

Provides:
- Database fixtures (test_db, db_session)
- FastAPI client fixtures
- Authentication fixtures (test users, tokens)
- Mock data fixtures (scopes, curations, evidence)
- External API mocks
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.models import (
    CurationNew,
    EvidenceItem,
    Gene,
    Scope,
    ScopeMembership,
    UserNew,
    WorkflowPair,
)

# Test database URL - in-memory SQLite for speed
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """Create test database engine with SQLite"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn: Any, connection_record: Any) -> None:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = testing_session_local()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """FastAPI test client with database override"""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# User Fixtures
# =============================================================================


@pytest.fixture
def test_user_admin(db_session: Session) -> UserNew:
    """Create test admin user"""
    user = UserNew(
        id=uuid4(),
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        name="Admin User",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_curator(db_session: Session, test_scope: Scope) -> UserNew:
    """Create test curator user (user role with curator scope membership)"""
    user = UserNew(
        id=uuid4(),
        email="curator@test.com",
        hashed_password=get_password_hash("curator123"),
        name="Curator User",
        role="user",  # User role at application level
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Add scope membership with curator role
    membership = ScopeMembership(
        scope_id=test_scope.id,
        user_id=user.id,
        role="curator",  # Scope-specific role
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_viewer(db_session: Session, test_scope: Scope) -> UserNew:
    """Create test viewer user (user role with viewer scope membership)"""
    user = UserNew(
        id=uuid4(),
        email="viewer@test.com",
        hashed_password=get_password_hash("viewer123"),
        name="Viewer User",
        role="user",  # User role at application level
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Add scope membership as viewer
    membership = ScopeMembership(
        scope_id=test_scope.id,
        user_id=user.id,
        role="viewer",  # Scope-specific role
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(test_user_admin: UserNew) -> str:
    """JWT token for admin user"""
    # Must match production token format: sub=user_id (UUID), not email
    return create_access_token(
        data={
            "sub": str(test_user_admin.id),
            "email": test_user_admin.email,
            "role": test_user_admin.role.value,
        }
    )


@pytest.fixture
def curator_token(test_user_curator: UserNew) -> str:
    """JWT token for curator user"""
    # Must match production token format: sub=user_id (UUID), not email
    return create_access_token(
        data={
            "sub": str(test_user_curator.id),
            "email": test_user_curator.email,
            "role": test_user_curator.role.value,
        }
    )


@pytest.fixture
def viewer_token(test_user_viewer: UserNew) -> str:
    """JWT token for viewer user"""
    # Must match production token format: sub=user_id (UUID), not email
    return create_access_token(
        data={
            "sub": str(test_user_viewer.id),
            "email": test_user_viewer.email,
            "role": test_user_viewer.role.value,
        }
    )


# =============================================================================
# Data Fixtures
# =============================================================================


@pytest.fixture
def test_scope(db_session: Session) -> Scope:
    """Create test scope"""
    scope = Scope(
        id=uuid4(),
        name="test-scope",
        display_name="Test Scope",
        description="Test scope for unit tests",
        is_public=False,
        is_active=True,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope


@pytest.fixture
def test_public_scope(db_session: Session) -> Scope:
    """Create public test scope"""
    scope = Scope(
        id=uuid4(),
        name="public-scope",
        display_name="Public Test Scope",
        description="Public test scope",
        is_public=True,
        is_active=True,
    )
    db_session.add(scope)
    db_session.commit()
    db_session.refresh(scope)
    return scope


@pytest.fixture
def test_gene(db_session: Session) -> Gene:
    """Create test gene"""
    import hashlib

    gene_data = "HGNC:1100:BRCA1"
    record_hash = hashlib.sha256(gene_data.encode()).hexdigest()

    gene = Gene(
        id=uuid4(),
        hgnc_id="HGNC:1100",
        approved_symbol="BRCA1",
        record_hash=record_hash,
        previous_symbols=["BRCC1"],
        alias_symbols=["FANCS", "RNF53"],
        chromosome="17",
        location="17q21.31",
        details={"approved_name": "BRCA1 DNA repair associated"},
    )
    db_session.add(gene)
    db_session.commit()
    db_session.refresh(gene)
    return gene


@pytest.fixture
def test_workflow_pair(db_session: Session) -> WorkflowPair:
    """Create test workflow pair"""
    workflow_pair = WorkflowPair(
        id=uuid4(),
        name="test-workflow",
        version="1.0",
    )
    db_session.add(workflow_pair)
    db_session.commit()
    db_session.refresh(workflow_pair)
    return workflow_pair


@pytest.fixture
def test_curation(
    db_session: Session,
    test_scope: Scope,
    test_gene: Gene,
    test_user_curator: UserNew,
    test_workflow_pair: WorkflowPair,
) -> CurationNew:
    """Create test curation"""
    curation = CurationNew(
        id=uuid4(),
        scope_id=test_scope.id,
        gene_id=test_gene.id,
        workflow_pair_id=test_workflow_pair.id,
        workflow_stage="curation",
        evidence_data={"status": "in_progress"},
        created_by=test_user_curator.id,
    )
    db_session.add(curation)
    db_session.commit()
    db_session.refresh(curation)
    return curation


@pytest.fixture
def test_evidence_item(
    db_session: Session,
    test_curation: CurationNew,
    test_user_curator: UserNew,
) -> EvidenceItem:
    """Create test evidence item"""
    evidence = EvidenceItem(
        id=uuid4(),
        curation_id=test_curation.id,
        evidence_category="case_level",
        evidence_type="genetic",
        evidence_data={
            "proband_count": 10,
            "segregation_strength": "strong",
            "phenotype_specificity": "high",
        },
        computed_score=5.0,
        score_metadata={"method": "clingen_sop_v11"},
        validation_status="valid",
        created_by=test_user_curator.id,
        updated_by=test_user_curator.id,
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)
    return evidence


# =============================================================================
# Mock Fixtures for External APIs
# =============================================================================


@pytest.fixture
def mock_hgnc_api() -> Generator[MagicMock, None, None]:
    """Mock HGNC API responses"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "docs": [
                    {
                        "symbol": "BRCA1",
                        "hgnc_id": "HGNC:1100",
                        "name": "BRCA1 DNA repair associated",
                        "status": "Approved",
                        "alias_symbol": ["BRCC1", "FANCS"],
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_pubmed_api() -> Generator[MagicMock, None, None]:
    """Mock PubMed API responses"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>31558469</PMID>
                    <Article>
                        <ArticleTitle>Test Article Title</ArticleTitle>
                        <AuthorList>
                            <Author><LastName>Smith</LastName></Author>
                        </AuthorList>
                        <Journal>
                            <Title>Test Journal</Title>
                            <JournalIssue>
                                <PubDate><Year>2019</Year></PubDate>
                            </JournalIssue>
                        </Journal>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_hpo_api() -> Generator[MagicMock, None, None]:
    """Mock HPO/OLS API responses"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "label": "Seizure",
            "obo_id": "HP:0001250",
            "description": ["A seizure is an abnormal..."],
            "synonyms": ["Epileptic seizure", "Fits"],
        }
        mock_get.return_value = mock_response
        yield mock_get


# =============================================================================
# Parametrization Helpers
# =============================================================================


def pytest_configure(config: Any) -> None:
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
