"""MCP OAuth 2.1 authorization server (#462, phase 2) on the MCP SDK's handlers.

The SDK serves discovery (RFC 8414, RFC 9728), client registration (RFC 7591),
/authorize and /token with PKCE S256; this module only stores their state (064).
The access token is a personal access token row, so the API applies RLS, scope roles,
D1 and the PAT account-operation block to OAuth calls unchanged. Codes, refresh tokens
and client secrets are stored as sha256 hashes only and never logged.
"""

import base64
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastmcp.server.auth import AccessToken, OAuthProvider
from fastmcp.server.auth.auth import TokenHandler
from mcp.server.auth.middleware.client_auth import ClientAuthenticator
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.routes import cors_middleware
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from sqlalchemy import CursorResult, select, text, update
from sqlalchemy.orm import InstrumentedAttribute, Session
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.routing import Route

from app.core.config import settings
from app.core.database import RLS_USER_KEY, apply_rls_user
from app.core.logging import get_logger
from app.core.security import (
    generate_personal_access_token,
    hash_personal_access_token as _hash,
)
from app.mcp.auth import _session, pat_owner
from app.models import PersonalAccessToken
from app.models.oauth import OAuthClient, OAuthGrant

logger = get_logger(__name__)


SCOPES = ["read", "write"]
CONSENT_TTL = timedelta(minutes=10)
CODE_TTL = timedelta(minutes=5)
ACCESS_TOKEN_TTL = timedelta(hours=1)
REFRESH_TOKEN_TTL = timedelta(days=30)
REFRESH_PREFIX = "gc_ort_"  # never a bearer credential: the API accepts only gc_pat_
_LOOPBACK = {"localhost", "127.0.0.1", "::1"}
# Registration and /authorize are anonymous: bound what a caller can make us store
MAX_CLIENT_NAME = 100  # the PAT name it becomes is 100 characters
MAX_REDIRECT_URIS = 10
MAX_URI = 2000
MAX_CLIENT_METADATA = 8192  # bytes of JSON, every other metadata field included
MAX_STATE = 512


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)  # SQLite: naive UTC


def _rows(result: Any) -> int:
    return cast(CursorResult[Any], result).rowcount


def _grant_by_hash(
    db: Session, token_hash: str, column: InstrumentedAttribute[str | None]
) -> OAuthGrant | None:
    """The grant holding this code or refresh token hash, read as its owner."""
    if db.get_bind().dialect.name == "postgresql":
        # No RLS user yet: the SECURITY DEFINER function (064) names the owner
        owner = db.scalar(text("SELECT oauth_grant_owner(:h)"), {"h": token_hash})
        if owner is None:
            return None
        db.info[RLS_USER_KEY] = str(owner)
        apply_rls_user(db.connection(), str(owner))
    return db.scalar(select(OAuthGrant).where(column == token_hash))


def _pending(db: Session, request_id: UUID) -> OAuthGrant | None:
    grant = db.get(OAuthGrant, request_id)
    if grant is None or grant.user_id is not None or _aware(grant.expires_at) < _now():
        return None
    return grant


def pending_request(db: Session, request_id: UUID) -> dict[str, Any] | None:
    """What the consent page shows: the client, where it redirects, the scopes."""
    grant = _pending(db, request_id)
    if grant is None:
        return None
    client = db.get(OAuthClient, grant.client_id)
    name = client.metadata_.get("client_name") if client else None
    return {
        "client_name": name or grant.client_id,
        "redirect_uri": grant.params["redirect_uri"],
        "scopes": grant.params["scopes"],
    }


def consent(db: Session, request_id: UUID, user_id: UUID, approve: bool) -> str | None:
    """Bind a pending request to the signed-in user; the client's redirect URL."""
    grant = _pending(db, request_id)
    if grant is None:
        return None
    params = grant.params
    if not approve:
        db.delete(grant)
        db.commit()
        return construct_redirect_uri(
            params["redirect_uri"], error="access_denied", state=params["state"]
        )
    code = secrets.token_urlsafe(32)
    bound = db.execute(
        update(OAuthGrant)
        .where(OAuthGrant.id == grant.id, OAuthGrant.user_id.is_(None))
        .values(user_id=user_id, code_hash=_hash(code), expires_at=_now() + CODE_TTL)
    )
    db.commit()
    if not _rows(bound):
        return None
    logger.info("OAuth consent given", client_id=grant.client_id, user_id=str(user_id))
    return construct_redirect_uri(
        params["redirect_uri"], code=code, state=params["state"]
    )


async def _presented_secret(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Basic "):
        try:
            return unquote(base64.b64decode(header[6:]).decode().split(":", 1)[1])
        except (ValueError, IndexError):  # binascii and Unicode errors are ValueErrors
            return None
    secret = (await request.form()).get("client_secret")
    return secret if isinstance(secret, str) else None


class _PresentedSecretView:
    """get_client for the SDK's plaintext comparison: the stored hash becomes the
    presented secret when they match, else an unguessable value (never the hash)."""

    def __init__(self, provider: "McpOAuthProvider", presented: str | None) -> None:
        self._provider = provider
        self._presented = presented

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        client = await self._provider.get_client(client_id)
        if client is None or client.client_secret is None:
            return client
        ok = self._presented is not None and hmac.compare_digest(
            _hash(self._presented), client.client_secret
        )
        secret = self._presented if ok else secrets.token_hex(32)
        return client.model_copy(update={"client_secret": secret})


class HashedSecretAuthenticator(ClientAuthenticator):
    """The SDK's client authentication against client secrets stored as sha256."""

    async def authenticate_request(
        self, request: Request
    ) -> OAuthClientInformationFull:
        provider = cast("McpOAuthProvider", self.provider)
        view = _PresentedSecretView(provider, await _presented_secret(request))
        return await ClientAuthenticator(cast(Any, view)).authenticate_request(request)


class McpOAuthProvider(OAuthProvider):
    """Accepts personal access tokens and issues OAuth ones (which are PAT rows)."""

    def __init__(self, app: FastAPI) -> None:
        super().__init__(
            base_url=settings.GENE_CURATOR_PUBLIC_URL,
            client_registration_options=ClientRegistrationOptions(
                enabled=True, valid_scopes=SCOPES, default_scopes=SCOPES
            ),
        )
        self._app = app

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        token = TokenHandler(
            provider=self, client_authenticator=HashedSecretAuthenticator(self)
        )
        return [
            Route(
                "/token",
                endpoint=cors_middleware(token.handle, ["POST", "OPTIONS"]),
                methods=["POST", "OPTIONS"],
            )
            if route.path == "/token"
            else route
            for route in super().get_routes(mcp_path)
        ]

    async def load_access_token(self, token: str) -> AccessToken | None:
        found: Any = await run_in_threadpool(pat_owner, self._app, token)
        if found is None:
            return None
        user_id, scopes, name, role = found
        # role only shapes tools/list (server.CallerToolFilter); the API re-checks it
        return AccessToken(
            token=token,
            client_id=name,
            scopes=scopes,
            claims={"sub": user_id, "role": role},
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        # /revoke is not served (no revocation_options): revoke in the token list
        raise NotImplementedError

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return await run_in_threadpool(self._get_client, client_id)

    def _get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        with _session(self._app) as db:
            row = db.get(OAuthClient, client_id)
            if row is None:
                return None
            return OAuthClientInformationFull.model_validate(
                {**row.metadata_, "client_secret": row.client_secret_hash}
            )

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        uris = client_info.redirect_uris or []
        if (
            len(client_info.client_name or "") > MAX_CLIENT_NAME
            or len(uris) > MAX_REDIRECT_URIS
            or any(len(str(uri)) > MAX_URI for uri in uris)
            or len(client_info.model_dump_json()) > MAX_CLIENT_METADATA
        ):
            raise RegistrationError(
                "invalid_client_metadata",
                f"client_name at most {MAX_CLIENT_NAME} characters, at most "
                f"{MAX_REDIRECT_URIS} redirect URIs of {MAX_URI} characters, metadata "
                f"at most {MAX_CLIENT_METADATA} bytes",
            )
        for uri in uris:
            parsed = urlparse(str(uri))
            if parsed.scheme != "https" and not (
                parsed.scheme == "http" and parsed.hostname in _LOOPBACK
            ):
                raise RegistrationError(
                    "invalid_redirect_uri", "redirect URIs must be HTTPS or loopback"
                )
        await run_in_threadpool(self._register, client_info)

    def _register(self, info: OAuthClientInformationFull) -> None:
        with _session(self._app) as db:
            db.add(
                OAuthClient(
                    client_id=info.client_id,
                    client_secret_hash=_hash(info.client_secret)
                    if info.client_secret
                    else None,
                    metadata_=info.model_dump(
                        mode="json", exclude={"client_secret"}, exclude_none=True
                    ),
                )
            )
            db.commit()
        logger.info("OAuth client registered", client_id=info.client_id)

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        # RFC 7636: an S256 challenge is 43 characters; the redirect URI was matched
        if (
            len(params.code_challenge) != 43
            or len(params.state or "") > MAX_STATE
            or len(params.resource or "") > MAX_URI
        ):
            raise AuthorizeError(
                "invalid_request",
                f"code_challenge must be 43 characters (S256), state at most "
                f"{MAX_STATE} and resource at most {MAX_URI}",
            )
        return await run_in_threadpool(self._authorize, client, params)

    def _authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Store the request and send the user to the consent page."""
        # ponytail: expired pending requests are never deleted; add a periodic cleanup
        # (DELETE FROM oauth_grants WHERE user_id IS NULL AND expires_at < NOW()) if
        # anonymous /authorize calls ever pile up
        request_id = uuid4()
        scopes = params.scopes or (client.scope or " ".join(SCOPES)).split()
        with _session(self._app) as db:
            db.add(
                OAuthGrant(
                    id=request_id,
                    client_id=client.client_id,
                    params={**params.model_dump(mode="json"), "scopes": scopes},
                    expires_at=_now() + CONSENT_TTL,
                )
            )
            db.commit()
        return (
            f"{settings.GENE_CURATOR_FRONTEND_URL}/oauth/consent?request={request_id}"
        )

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return await run_in_threadpool(self._load_code, client, authorization_code)

    def _load_code(
        self, client: OAuthClientInformationFull, code: str
    ) -> AuthorizationCode | None:
        with _session(self._app) as db:
            grant = _grant_by_hash(db, _hash(code), OAuthGrant.code_hash)
            if grant is None or grant.client_id != client.client_id:
                return None
            p = grant.params
            return AuthorizationCode(
                code=code,
                scopes=p["scopes"],
                expires_at=_aware(grant.expires_at).timestamp(),
                client_id=grant.client_id,
                code_challenge=p["code_challenge"],
                redirect_uri=p["redirect_uri"],
                redirect_uri_provided_explicitly=p["redirect_uri_provided_explicitly"],
                resource=p.get("resource"),
                subject=str(grant.user_id),
            )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        return await run_in_threadpool(self._exchange_code, client, authorization_code)

    def _exchange_code(
        self, client: OAuthClientInformationFull, code: AuthorizationCode
    ) -> OAuthToken:
        access, refresh = generate_personal_access_token(), _refresh_token()
        scopes = sorted(set(code.scopes))
        with _session(self._app) as db:
            grant = _grant_by_hash(db, _hash(code.code), OAuthGrant.code_hash)
            if grant is None or grant.user_id is None:
                raise TokenError("invalid_grant", "authorization code was already used")
            pat = PersonalAccessToken(
                id=uuid4(),
                user_id=grant.user_id,
                name=f"OAuth: {client.client_name or client.client_id}"[:100],
                token_hash=_hash(access),
                token_prefix=access[:12],
                scopes=scopes,
                expires_at=_now() + ACCESS_TOKEN_TTL,
            )
            db.add(pat)
            db.flush()
            # Single use: of two parallel exchanges only one still finds the code
            used = db.execute(
                update(OAuthGrant)
                .where(
                    OAuthGrant.id == grant.id, OAuthGrant.code_hash == _hash(code.code)
                )
                .values(
                    code_hash=None,
                    refresh_token_hash=_hash(refresh),
                    access_token_id=pat.id,
                    expires_at=_now() + REFRESH_TOKEN_TTL,
                )
            )
            if not _rows(used):
                db.rollback()
                raise TokenError("invalid_grant", "authorization code was already used")
            db.commit()
            logger.info("OAuth tokens issued", client_id=grant.client_id)
        return _token_response(access, refresh, scopes)

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        return await run_in_threadpool(self._load_refresh, client, refresh_token)

    def _load_refresh(
        self, client: OAuthClientInformationFull, token: str
    ) -> RefreshToken | None:
        with _session(self._app) as db:
            grant = _grant_by_hash(db, _hash(token), OAuthGrant.refresh_token_hash)
            if grant is None or grant.client_id != client.client_id:
                return None
            pat = db.get(PersonalAccessToken, grant.access_token_id)
            if pat is None or pat.revoked_at is not None:  # revoked in the token list
                return None
            return RefreshToken(
                token=token,
                client_id=grant.client_id,
                scopes=list(pat.scopes),
                expires_at=int(_aware(grant.expires_at).timestamp()),
                subject=str(grant.user_id),
            )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        return await run_in_threadpool(self._rotate, refresh_token, scopes)

    def _rotate(self, old: RefreshToken, requested: list[str]) -> OAuthToken:
        """Rotation: a new refresh token, and the grant's access token gets a new hash."""
        access, refresh = generate_personal_access_token(), _refresh_token()
        scopes = sorted(set(requested))
        args = {
            "old": _hash(old.token),
            "new": _hash(refresh),
            "access": _hash(access),
            "prefix": access[:12],
            "scopes": scopes,
        }
        with _session(self._app) as db:
            if db.get_bind().dialect.name == "postgresql":
                # app_user may not update a PAT (056); the 064 function rotates it
                rotated = bool(
                    db.scalar(
                        text(
                            "SELECT oauth_rotate_refresh_token("
                            ":old, :new, :access, :prefix, CAST(:scopes AS TEXT[]))"
                        ),
                        args,
                    )
                )
            else:
                rotated = _rotate_in_sqlite(db, args)
            if not rotated:
                db.rollback()
                raise TokenError("invalid_grant", "refresh token was used or revoked")
            db.commit()
        return _token_response(access, refresh, scopes)


def _rotate_in_sqlite(db: Session, args: dict[str, Any]) -> bool:
    """oauth_rotate_refresh_token (064) for the SQLite test database."""
    grant = db.scalar(
        select(OAuthGrant).where(OAuthGrant.refresh_token_hash == args["old"])
    )
    if grant is None:
        return False
    pat = db.get(PersonalAccessToken, grant.access_token_id)
    if pat is None or pat.revoked_at is not None:
        return False
    grant.refresh_token_hash = args["new"]
    grant.expires_at = _now() + REFRESH_TOKEN_TTL
    pat.token_hash, pat.token_prefix = args["access"], args["prefix"]
    pat.scopes, pat.expires_at = args["scopes"], _now() + ACCESS_TOKEN_TTL
    return True


def _refresh_token() -> str:
    return REFRESH_PREFIX + secrets.token_urlsafe(32)


def _token_response(access: str, refresh: str, scopes: list[str]) -> OAuthToken:
    return OAuthToken(
        access_token=access,
        token_type="Bearer",  # noqa: S106  # nosec B106 (the scheme, not a secret)
        expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
        refresh_token=refresh,
        scope=" ".join(scopes),
    )


def mount_oauth_routes(app: FastAPI, auth: McpOAuthProvider, mcp_path: str) -> None:
    """The OAuth routes live at the API root, where clients discover them; the MCP
    app itself is mounted only at its exact path."""
    taken = {getattr(route, "path", None) for route in app.router.routes}
    app.router.routes.extend(
        r for r in auth.get_routes(mcp_path) if r.path not in taken
    )
