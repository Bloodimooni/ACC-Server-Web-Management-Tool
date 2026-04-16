from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.auth import oidc
from app.auth.local import verify_user
from app.auth.session import create_session, delete_session
from app.config import settings

router = APIRouter(prefix="/auth")


@router.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    if not verify_user(username, password):
        return RedirectResponse("/login?error=1", status_code=302)
    response = RedirectResponse("/", status_code=302)
    create_session(response, username, "local")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    delete_session(response)
    return response


@router.get("/providers")
async def providers():
    return {"oidc_enabled": settings.OIDC_ENABLED}


@router.get("/oidc/login")
async def oidc_login():
    if not settings.OIDC_ENABLED:
        raise HTTPException(404, "OIDC not enabled")
    # Build the redirect; build_redirect() sets the flow cookie on the response
    response = RedirectResponse("/", status_code=302)  # placeholder target
    auth_url = await oidc.build_redirect(response)
    # Replace the redirect target with the real Authentik URL
    response.headers["location"] = auth_url
    return response


@router.get("/oidc/callback")
async def oidc_callback(request: Request):
    if not settings.OIDC_ENABLED:
        raise HTTPException(404, "OIDC not enabled")
    response = RedirectResponse("/", status_code=302)
    username = await oidc.handle_callback(request, response)
    create_session(response, username, "oidc")
    return response
