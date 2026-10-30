"""MCP OAuth 2.1 (#462 phase 2): discovery, registration, consent, PKCE, rotation."""

import base64
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_personal_access_token
from app.crud import personal_access_token as pat_crud
from app.models import PersonalAccessToken, UserNew
from app.models.oauth import OAuthClient, OAuthGrant
from app.schemas.personal_access_token import PersonalAccessTokenCreate

pytestmark = pytest.mark.unit

REDIRECT = "http://localhost:33418/callback"
ACCEPT = {"Accept": "application/json, text/event-stream"}


def register(tc: TestClient, **extra: Any) -> dict[str, Any]:
    body = {
        "client_name": "Claude Code",
        "redirect_uris": [REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        **extra,
    }
    r = tc.post("/register", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


def authorize(tc: TestClient, client_id: str, challenge: str, **extra: str) -> str:
    r = tc.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "st4te",
            **extra,
        },
        follow_redirects=False,
    )
    assert r.status_code == 302, r.text
    consent_url = urlparse(r.headers["location"])
    assert consent_url.path == "/oauth/consent"
    return parse_qs(consent_url.query)["request"][0]


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).decode().rstrip("=")


def approve(tc: TestClient, session: str, request_id: str) -> str:
    r = tc.post(
        f"/api/v1/oauth/authorizations/{request_id}",
        json={"approve": True},
        headers={"Authorization": f"Bearer {session}"},
    )
    assert r.status_code == 200, r.text
    query = parse_qs(urlparse(r.json()["redirect_url"]).query)
    assert query["state"] == ["st4te"]
    return query["code"][0]


def exchange(
    tc: TestClient, client_id: str, code: str, verifier: str, **extra: str
) -> Any:
    return tc.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": REDIRECT,
            "code_verifier": verifier,
            **extra,
        },
    )


def refresh(tc: TestClient, client_id: str, token: str) -> Any:
    return tc.post(
        "/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": token,
        },
    )


def whoami(tc: TestClient, token: str) -> Any:
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "read_users_me", "arguments": {}},
    }
    return tc.post(
        "/mcp", json=body, headers={**ACCEPT, "Authorization": f"Bearer {token}"}
    )


def grant_tokens(tc: TestClient, session: str) -> tuple[str, dict[str, Any]]:
    client_id = register(tc)["client_id"]
    verifier, challenge = pkce()
    code = approve(tc, session, authorize(tc, client_id, challenge))
    r = exchange(tc, client_id, code, verifier)
    assert r.status_code == 200, r.text
    return client_id, dict(r.json())


def test_discovery_metadata_is_served_at_the_root(client: TestClient) -> None:
    server = client.get("/.well-known/oauth-authorization-server").json()
    assert server["code_challenge_methods_supported"] == ["S256"]
    assert server["registration_endpoint"].endswith("/register")
    assert server["scopes_supported"] == ["read", "write"]
    for path in ("/mcp", "/mcp/full"):
        resource = client.get(f"/.well-known/oauth-protected-resource{path}").json()
        assert resource["resource"].endswith(path)
        assert resource["authorization_servers"] == [server["issuer"]]
    challenge = client.post("/mcp", json={}, headers=ACCEPT)
    assert challenge.status_code == 401
    assert "oauth-protected-resource/mcp" in challenge.headers["www-authenticate"]


def test_full_flow_acts_as_the_user_with_rotation_and_no_secret_leaks(
    client: TestClient,
    curator_token: str,
    test_user_curator: UserNew,
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    client_id = register(client)["client_id"]
    verifier, challenge = pkce()
    request_id = authorize(client, client_id, challenge)
    shown = client.get(
        f"/api/v1/oauth/authorizations/{request_id}",
        headers={"Authorization": f"Bearer {curator_token}"},
    )
    assert shown.json() == {
        "client_name": "Claude Code",
        "redirect_uri": REDIRECT,
        "scopes": ["read", "write"],
    }
    code = approve(client, curator_token, request_id)
    assert exchange(client, client_id, code, "wrong-verifier").status_code == 401
    tokens = exchange(client, client_id, code, verifier).json()
    assert tokens["expires_in"] == 3600 and tokens["scope"] == "read write"
    assert exchange(client, client_id, code, verifier).status_code == 401  # single use

    me = whoami(client, tokens["access_token"])
    assert test_user_curator.email in me.text, me.text
    pat = db_session.query(PersonalAccessToken).one()
    assert pat.name == "OAuth: Claude Code" and pat.user_id == test_user_curator.id

    rotated = refresh(client, client_id, tokens["refresh_token"]).json()
    assert whoami(client, tokens["access_token"]).status_code == 401
    assert whoami(client, rotated["access_token"]).status_code == 200
    assert refresh(client, client_id, tokens["refresh_token"]).status_code == 401
    assert db_session.query(PersonalAccessToken).count() == 1  # one row per grant

    grant = db_session.query(OAuthGrant).one()
    secrets_issued = [code, tokens["access_token"], tokens["refresh_token"]]
    secrets_issued += [rotated["access_token"], rotated["refresh_token"]]
    assert grant.refresh_token_hash == hash_personal_access_token(
        rotated["refresh_token"]
    )
    assert grant.code_hash is None
    for value in secrets_issued:
        assert value not in caplog.text
        assert value not in str(grant.params)
    assert "OAuth tokens issued" in caplog.text


def test_revoked_or_expired_access_ends_the_grant(
    client: TestClient, curator_token: str, db_session: Session
) -> None:
    client_id, tokens = grant_tokens(client, curator_token)
    pat = db_session.query(PersonalAccessToken).one()
    pat.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    assert whoami(client, tokens["access_token"]).status_code == 401
    rotated = refresh(
        client, client_id, tokens["refresh_token"]
    ).json()  # expiry: refresh
    assert whoami(client, rotated["access_token"]).status_code == 200

    revoked = client.delete(
        f"/api/v1/me/tokens/{pat.id}",
        headers={"Authorization": f"Bearer {curator_token}"},
    )
    assert revoked.status_code == 204, revoked.text
    assert whoami(client, rotated["access_token"]).status_code == 401
    assert refresh(client, client_id, rotated["refresh_token"]).status_code == 401


def test_deny_and_unknown_requests(client: TestClient, curator_token: str) -> None:
    client_id = register(client)["client_id"]
    request_id = authorize(client, client_id, pkce()[1])
    auth = {"Authorization": f"Bearer {curator_token}"}
    denied = client.post(
        f"/api/v1/oauth/authorizations/{request_id}",
        json={"approve": False},
        headers=auth,
    )
    query = parse_qs(urlparse(denied.json()["redirect_url"]).query)
    assert query == {"error": ["access_denied"], "state": ["st4te"]}
    gone = client.get(f"/api/v1/oauth/authorizations/{request_id}", headers=auth)
    assert gone.status_code == 404
    again = client.post(
        f"/api/v1/oauth/authorizations/{request_id}",
        json={"approve": True},
        headers=auth,
    )
    assert again.status_code == 404


def test_a_token_cannot_give_consent(
    client: TestClient, test_user_curator: UserNew, db_session: Session
) -> None:
    """A PAT (and so an OAuth token) may not mint a new grant, e.g. read -> write."""
    obj = PersonalAccessTokenCreate(
        name="script", expires_at=datetime.now(UTC) + timedelta(days=1), scopes=["read"]
    )
    token = pat_crud.create(db_session, user_id=test_user_curator.id, obj_in=obj)[1]
    request_id = authorize(client, register(client)["client_id"], pkce()[1])
    r = client.post(
        f"/api/v1/oauth/authorizations/{request_id}",
        json={"approve": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_redirect_uris_must_be_https_or_loopback(client: TestClient) -> None:
    for uri in ("javascript:alert(1)", "http://evil.example/cb"):
        r = client.post(
            "/register",
            json={"redirect_uris": [uri], "token_endpoint_auth_method": "none"},
        )
        assert r.status_code == 400, uri
    register(client, redirect_uris=["https://claude.ai/api/mcp/auth_callback"])


def test_client_secret_is_stored_hashed_and_checked(
    client: TestClient, curator_token: str, db_session: Session
) -> None:
    info = register(client, token_endpoint_auth_method="client_secret_post")
    secret = info["client_secret"]
    stored = db_session.get(OAuthClient, info["client_id"])
    assert stored is not None
    assert stored.client_secret_hash == hash_personal_access_token(secret)
    assert secret not in str(stored.metadata_)

    def attempt(presented: str | None) -> int:
        verifier, challenge = pkce()
        code = approve(
            client, curator_token, authorize(client, info["client_id"], challenge)
        )
        extra = {"client_secret": presented} if presented else {}
        return int(
            exchange(client, info["client_id"], code, verifier, **extra).status_code
        )

    assert attempt(None) == 401
    assert attempt("wrong") == 401
    assert attempt(stored.client_secret_hash) == 401  # the hash is no credential
    assert attempt(secret) == 200

    basic = base64.b64encode(f"{info['client_id']}:{secret}".encode()).decode()
    verifier, challenge = pkce()
    code = approve(
        client, curator_token, authorize(client, info["client_id"], challenge)
    )
    r = client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "client_id": info["client_id"],
            "code": code,
            "redirect_uri": REDIRECT,
            "code_verifier": verifier,
        },
        headers={"Authorization": f"Basic {basic}"},
    )
    assert r.status_code == 401  # registered for client_secret_post, not basic


@pytest.mark.parametrize(
    "extra",
    [
        {"client_name": "x" * 101},
        {"redirect_uris": [f"http://localhost:{1000 + i}/cb" for i in range(11)]},
        {"redirect_uris": ["https://claude.ai/" + "a" * 2000]},
        {"software_id": "s" * 9000},
    ],
)
def test_registration_metadata_is_bounded(
    client: TestClient, extra: dict[str, Any]
) -> None:
    body = {"redirect_uris": [REDIRECT], "token_endpoint_auth_method": "none", **extra}
    r = client.post("/register", json=body)
    assert r.status_code == 400, r.text
    assert r.json()["error"] == "invalid_client_metadata"
    register(client, client_name="x" * 100)  # the limit itself is accepted


@pytest.mark.parametrize(
    "extra",
    [{"code_challenge": "short"}, {"state": "s" * 513}, {"resource": "r" * 2001}],
)
def test_authorize_parameters_are_bounded(
    client: TestClient, db_session: Session, extra: dict[str, str]
) -> None:
    client_id = register(client)["client_id"]
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT,
        "code_challenge": pkce()[1],
        "code_challenge_method": "S256",
        **extra,
    }
    r = client.get("/authorize", params=params, follow_redirects=False)
    # the redirect URI is registered, so the error goes back to the client (RFC 6749 4.1.2.1)
    assert r.status_code == 302
    location = urlparse(r.headers["location"])
    assert location.netloc == "localhost:33418"
    assert parse_qs(location.query)["error"] == ["invalid_request"]
    assert db_session.query(OAuthGrant).count() == 0


def test_production_refuses_a_plain_http_issuer() -> None:
    base = {"DATABASE_URL": "postgresql://u:p@h/x", "SECRET_KEY": "x"}
    with pytest.raises(ValidationError, match="must be https"):
        Settings(
            **base, ENVIRONMENT="production", GENE_CURATOR_PUBLIC_URL="http://api.org"
        )
    ok = Settings(
        **base, ENVIRONMENT="production", GENE_CURATOR_PUBLIC_URL="https://api.org"
    )
    assert ok.GENE_CURATOR_PUBLIC_URL == "https://api.org"
    dev = Settings(
        **base, ENVIRONMENT="development", GENE_CURATOR_PUBLIC_URL="http://gc.lan:8051"
    )
    assert dev.GENE_CURATOR_PUBLIC_URL.startswith("http://")
