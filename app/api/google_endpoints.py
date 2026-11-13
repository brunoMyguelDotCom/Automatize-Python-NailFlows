"""Conexão OAuth de uma única agenda Google."""
import secrets
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.infrastructure.calendar.google import CalendarError
from app.api.security import require_admin

router = APIRouter(prefix="/auth/google", tags=["Google Calendar"])


def get_google(request: Request):
    calendar = request.app.state.google_calendar
    if calendar is None:
        raise HTTPException(503, "Configure CALENDAR_BACKEND=google e as credenciais no .env.")
    return calendar


@router.get("/connect")
def connect(google=Depends(get_google)):
    browser_secret = secrets.token_urlsafe(32)
    response = RedirectResponse(google.begin(browser_secret), status_code=302)
    response.set_cookie("google_oauth", browser_secret, max_age=600, httponly=True,
                        secure=urlparse(google.redirect_uri).scheme == "https", samesite="lax",
                        path="/auth/google")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.get("/callback")
def callback(request: Request, state: str = "", code: str = "", error: str = "", google=Depends(get_google)):
    try:
        if error or not state or not code:
            raise ValueError("Autorização não concluída. Inicie novamente.")
        google.finish(state, code, request.cookies.get("google_oauth", ""))
        response = JSONResponse({"message": "Google Calendar conectado. Você pode fechar esta página."})
    except ValueError as exc:
        response = JSONResponse({"detail": str(exc)}, status_code=400)
    except CalendarError as exc:
        response = JSONResponse({"detail": str(exc)}, status_code=503)
    response.delete_cookie("google_oauth", path="/auth/google")
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
