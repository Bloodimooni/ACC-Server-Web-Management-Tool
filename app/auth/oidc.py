import hashlib
import base64
import secrets
from urllib.parse import urlencode

import httpx
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from fastapi import HTTPException, Request, Response

from app.config import settings

_state_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="oidc-pkce")
_metadata_cache: dict | None = None


async def _get_metadata() -> dict:
    global _metadata_cache
    if not _metadata_cache:
        async with httpx.AsyncClient() as c:
            r = await c.get(settings.OIDC_DISCOVERY_URL, timeout=10)
            r.raise_for_status()
            _metadata_cache = r.json()
    return _metadata_cache


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


async def build_redirect(response: Response) -> str:
    """Sets the OIDC flow cookie on response and returns the authorization URL."""
    meta = await _get_metadata()
    state = secrets.token_urlsafe(32)
    verifier, challenge = _pkce_pair()

    signed = _state_serializer.dumps({"state": state, "verifier": verifier})
    response.set_cookie(
        "_oidc_flow", signed,
        httponly=True, samesite="lax",
        secure=settings.HTTPS_ENABLED, max_age=300,
    )

    params = {
        "response_type": "code",
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return meta["authorization_endpoint"] + "?" + urlencode(params)


async def handle_callback(request: Request, response: Response) -> str:
    """Validates the callback, exchanges code for tokens. Returns username."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        raise HTTPException(400, f"OIDC error: {request.query_params.get('error_description', error)}")
    if not code or not state:
        raise HTTPException(400, "Missing code or state parameter")

    flow_cookie = request.cookies.get("_oidc_flow")
    if not flow_cookie:
        raise HTTPException(400, "Missing OIDC flow cookie — please try signing in again")

    try:
        flow = _state_serializer.loads(flow_cookie, max_age=300)
    except SignatureExpired:
        raise HTTPException(400, "OIDC flow expired — please try again")
    except BadSignature:
        raise HTTPException(400, "Invalid OIDC state")

    if flow["state"] != state:
        raise HTTPException(400, "State mismatch — possible CSRF")

    meta = await _get_metadata()

    token_req: dict = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
        "code_verifier": flow["verifier"],
    }
    if settings.OIDC_CLIENT_SECRET:
        token_req["client_secret"] = settings.OIDC_CLIENT_SECRET

    async with httpx.AsyncClient() as c:
        tr = await c.post(meta["token_endpoint"], data=token_req, timeout=15)
        tr.raise_for_status()
        tokens = tr.json()

        ur = await c.get(
            meta["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=10,
        )
        ur.raise_for_status()
        userinfo = ur.json()

    response.delete_cookie("_oidc_flow")

    return (
        userinfo.get("preferred_username")
        or userinfo.get("email")
        or userinfo.get("sub")
    )
