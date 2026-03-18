"""Auth routes — Google OAuth login/callback + Twitter OAuth connect."""

import logging
import os
import secrets
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth")

BASE_DIR = Path(__file__).parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# OAuth setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def _get_app():
    import app as app_module
    return app_module


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login page. If already authenticated, redirect to dashboard."""
    a = _get_app()
    if a.check_auth(request):
        return RedirectResponse("/dashboard", status_code=302)

    error = request.query_params.get("error", "")
    return templates.TemplateResponse(
        request, "login.html", {"error": error, "active_page": "login"}
    )


@router.get("/google")
async def google_login(request: Request):
    """Initiate Google OAuth flow."""
    redirect_uri = request.url_for("google_callback")
    # Force HTTPS in production
    if os.environ.get("ENVIRONMENT") == "production":
        redirect_uri = str(redirect_uri).replace("http://", "https://")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback. Fail closed: any error = back to login."""
    a = _get_app()
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        log.warning("Google OAuth token exchange failed: %s", e)
        return RedirectResponse("/auth/login?error=auth_failed", status_code=302)

    userinfo = token.get("userinfo", {})
    email = userinfo.get("email", "").strip().lower()
    if not email:
        log.warning("Google OAuth returned no email")
        return RedirectResponse("/auth/login?error=no_email", status_code=302)

    conn = await db.get_connection(a.DB_PATH)
    try:
        user = await db.get_or_create_user(
            conn,
            email=email,
            name=userinfo.get("name", ""),
            picture=userinfo.get("picture", ""),
            google_sub=userinfo.get("sub", ""),
        )

        # Auto-promote admin emails
        if email in a.ADMIN_EMAILS and not user.get("is_admin"):
            await db.update_user(conn, user["id"], is_admin=1)

        request.session["user_id"] = user["id"]
        request.session["user_email"] = email
        request.session["user_name"] = user.get("name", email)

        # Redirect based on onboarding status
        if user.get("onboard_step", 0) < 3:
            return RedirectResponse("/onboard", status_code=302)
        return RedirectResponse("/dashboard", status_code=302)
    finally:
        await conn.close()


@router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse("/auth/login", status_code=302)


@router.get("/twitter")
async def twitter_connect(request: Request):
    """Initiate Twitter OAuth 1.0a flow for per-user posting credentials.
    This is a simplified placeholder — real implementation needs OAuth 1.0a request token flow."""
    a = _get_app()
    if not a.check_auth(request):
        return a._deny()

    # In production, this would redirect to Twitter's OAuth 1.0a authorize URL.
    # For now, redirect to settings with a message.
    return RedirectResponse("/settings?twitter=pending", status_code=302)


@router.post("/twitter/save")
async def twitter_save_tokens(request: Request):
    """Save Twitter OAuth tokens (manual entry for MVP).
    In production, these come from the OAuth callback."""
    a = _get_app()
    user_id = a.get_current_user_id(request)
    if not user_id:
        return a._deny()

    form = await request.form()
    access_token = str(form.get("twitter_access_token", "")).strip()
    access_secret = str(form.get("twitter_access_secret", "")).strip()
    username = str(form.get("twitter_username", "")).strip()[:50]

    if not access_token or not access_secret:
        return RedirectResponse("/settings?error=missing_tokens", status_code=302)

    # Encrypt tokens before storage
    try:
        import crypto
        enc_token = crypto.encrypt_token(access_token)
        enc_secret = crypto.encrypt_token(access_secret)
    except (ValueError, Exception) as e:
        log.error("Token encryption failed: %s", e)
        return RedirectResponse("/settings?error=encryption_failed", status_code=302)

    conn = await db.get_connection(a.DB_PATH)
    try:
        await db.update_user(conn, user_id,
            twitter_access_token=enc_token,
            twitter_access_secret=enc_secret,
            twitter_username=username,
        )
        # Mark onboarding step 3 complete if needed
        user = await db.get_user_by_id(conn, user_id)
        if user and user.get("onboard_step", 0) < 3:
            await db.update_user(conn, user_id, onboard_step=3)
    finally:
        await conn.close()

    return RedirectResponse("/settings?twitter=connected", status_code=302)
