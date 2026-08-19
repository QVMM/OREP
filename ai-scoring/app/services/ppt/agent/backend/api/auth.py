"""Authentication helpers for PPT job ownership.

The PPT agent runs as a sibling FastAPI service, so it must not trust a
frontend-only user filter. These helpers validate the same OREP JWT used by
the main backend and derive a stable owner key from tenant + user id.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import jwt
from fastapi import HTTPException, Request, WebSocket, status

DEFAULT_JWT_SECRET = "OREP_DEV_ONLY_CHANGE_ME_SECRET_KEY_64_CHARS_MINIMUM_2026"


@dataclass(frozen=True)
class PptOwner:
    user_id: str
    username: str
    role: str
    tenant_id: str

    @property
    def owner_key(self) -> str:
        return f"tenant:{self.tenant_id}:user:{self.user_id}"


def owner_from_request(request: Request) -> PptOwner:
    return owner_from_token(_extract_bearer_token(request.headers.get("authorization"), request.query_params.get("t")))


def owner_from_websocket(websocket: WebSocket) -> PptOwner:
    token = websocket.query_params.get("t") or websocket.query_params.get("token")
    return owner_from_token(_extract_bearer_token(websocket.headers.get("authorization"), token))


def owner_from_token(token: str | None) -> PptOwner:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录后再使用 PPT 生成功能。")

    secrets = _candidate_jwt_secrets()
    try:
        claims = _decode_orep_token(token, secrets)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录。") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态无效，请重新登录。") from exc

    user_id = str(claims.get("sub") or "").strip()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态缺少用户身份。")

    tenant_id = str(claims.get("tenantId") or "0").strip() or "0"
    return PptOwner(
        user_id=user_id,
        username=str(claims.get("username") or ""),
        role=str(claims.get("role") or ""),
        tenant_id=tenant_id,
    )


def _candidate_jwt_secrets() -> list[str]:
    """Return JWT secrets in the order the PPT service should trust them."""
    secrets: list[str] = []
    for env_name in ("OREP_JWT_SECRET", "JWT_SECRET"):
        env_secret = os.getenv(env_name)
        if env_secret:
            secrets.append(env_secret)

    local_secret = _read_backend_local_jwt_secret()
    if local_secret:
        secrets.append(local_secret)

    secrets.append(DEFAULT_JWT_SECRET)
    return list(dict.fromkeys(secret for secret in secrets if secret))


def _read_backend_local_jwt_secret() -> str | None:
    """Read the sibling Java backend's local JWT secret during local dev."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "backend" / ".env.local"
        if not candidate.exists():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == "OREP_JWT_SECRET":
                    return value.strip().strip("\"'")
        except OSError:
            return None
    return None


def _decode_orep_token(token: str, secrets: list[str]) -> dict:
    last_error: jwt.InvalidTokenError | None = None
    for secret in secrets:
        try:
            # The Java backend signs with JJWT's key-size based default, which
            # is HS512 for the current local secret. Keep HS256/HS384 for older
            # tokens that may still exist in dev browsers.
            return jwt.decode(token, secret, algorithms=["HS512", "HS384", "HS256"])
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise jwt.InvalidTokenError("No JWT secret configured.")


def ensure_job_owner(job, request: Request) -> PptOwner:
    owner = owner_from_request(request)
    if not job or not _owned_by(job, owner):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return owner


def ensure_session_owner(session, request: Request) -> PptOwner:
    owner = owner_from_request(request)
    if not session or not _owned_by(session, owner):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return owner


def filter_owned(items: Iterable, request: Request) -> list:
    owner = owner_from_request(request)
    return filter_owned_for_owner(items, owner)


def filter_owned_for_owner(items: Iterable, owner: PptOwner) -> list:
    return [item for item in items if _owned_by(item, owner)]


def can_claim_legacy_jobs(owner: PptOwner, has_owned_records: bool = False) -> bool:
    """Allow a trusted admin account to adopt pre-isolation PPT jobs.

    Jobs created before ownership isolation do not have an ``owner_key``.
    They must not be shown to every user, but the administrator who owns the
    historical workspace needs a one-time compatibility path. If the runtime
    has no owned records yet, this is the first post-upgrade history request,
    so the current authenticated user may claim the legacy local workspace.
    """
    username = (owner.username or "").strip().lower()
    role = (owner.role or "").strip().lower()
    return username == "admin" or "admin" in role or not has_owned_records


def _extract_bearer_token(authorization: str | None, fallback: str | None = None) -> str | None:
    header = (authorization or "").strip()
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    if header:
        return header
    fallback = (fallback or "").strip()
    return fallback or None


def _owned_by(item, owner: PptOwner) -> bool:
    return bool(getattr(item, "owner_key", None) and getattr(item, "owner_key", "") == owner.owner_key)
