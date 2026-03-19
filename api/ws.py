"""WebSocket token minting and real-time event handling.

Token: HMAC-SHA256({jti, sub, aud, project, exp})
jti uniqueness: Redis SET NX EX (one-time use)
Revocation: publish ws_revoke:{user_id} to Redis → handlers force-disconnect
"""

import hashlib
import hmac
import json
import logging
import os
import time
import uuid

logger = logging.getLogger("prd_forge_ws")

_DEFAULT_WS_SECRET = "dev-ws-secret-change-in-production-0000000000000000"
WS_TOKEN_SECRET = os.environ.get("WS_TOKEN_SECRET", _DEFAULT_WS_SECRET)
WS_TOKEN_TTL = int(os.environ.get("WS_TOKEN_TTL_SECONDS", "120"))

if WS_TOKEN_SECRET == _DEFAULT_WS_SECRET:
    import sys
    print(
        "WARNING: WS_TOKEN_SECRET is using the default dev value — "
        "set WS_TOKEN_SECRET env var in production",
        file=sys.stderr,
    )


def mint_ws_token(user_id: str, project_slug: str) -> str:
    """Create a short-lived HMAC token for WebSocket authentication."""
    payload = {
        "jti": str(uuid.uuid4()),
        "sub": user_id,
        "aud": "ws",
        "project": project_slug,
        "exp": int(time.time()) + WS_TOKEN_TTL,
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(
        WS_TOKEN_SECRET.encode(), payload_json.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload_json}.{sig}"


def verify_ws_token(token: str) -> dict | None:
    """Verify HMAC signature and TTL. Returns payload or None."""
    try:
        payload_json, sig = token.rsplit(".", 1)
    except ValueError:
        return None

    expected_sig = hmac.new(
        WS_TOKEN_SECRET.encode(), payload_json.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        logger.warning("WS token signature mismatch")
        return None

    payload = json.loads(payload_json)

    if payload.get("aud") != "ws":
        return None
    if payload.get("exp", 0) < time.time():
        logger.warning("WS token expired")
        return None

    return payload


# Event types for real-time updates
EVENT_TYPES = {
    "section_updated",
    "section_created",
    "section_deleted",
    "comment_added",
    "presence_update",
}
