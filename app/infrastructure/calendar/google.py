"""Google Calendar para uma conta por instalação do backend."""
import json
import os
import secrets
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, quote

from cryptography.fernet import Fernet
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.core.logging_config import logger
from app.domain.models import SyncStatus
from app.infrastructure.calendar.base import BaseCalendar

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
ROOT = Path(__file__).resolve().parents[3]


class CalendarError(Exception):
    """Erro de integração; detalhes e credenciais não devem chegar ao cliente."""


class GoogleCalendar(BaseCalendar):
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback").strip()
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip()
        if not all((self.client_id, self.client_secret, self.calendar_id)):
            raise ValueError("Configure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET e GOOGLE_CALENDAR_ID")
        uri = urlparse(self.redirect_uri)
        if uri.scheme != "https" and not (uri.scheme == "http" and uri.hostname in ("localhost", "127.0.0.1")):
            raise ValueError("GOOGLE_REDIRECT_URI deve usar HTTPS ou localhost")
        self.cipher = Fernet(os.environ["GOOGLE_TOKEN_ENCRYPTION_KEY"].encode())
        self.token_path = Path(os.getenv("GOOGLE_TOKEN_FILE", str(ROOT / ".secrets/google-token.enc")))
        if not self.token_path.is_absolute():
            self.token_path = ROOT / self.token_path
        self.lock = threading.RLock()
        self.pending = {}

    def _flow(self, **kwargs):
        return Flow.from_client_config({"web": {
            "client_id": self.client_id, "client_secret": self.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }}, scopes=SCOPES, redirect_uri=self.redirect_uri, **kwargs)

    def begin(self, browser_secret):
        flow = self._flow(autogenerate_code_verifier=True)
        url, state = flow.authorization_url(access_type="offline", prompt="consent")
        with self.lock:
            now = time.monotonic()
            self.pending = {k: v for k, v in self.pending.items() if v[0] > now}
            self.pending[state] = (now + 600, browser_secret, flow.code_verifier)
        return url

    def finish(self, state, code, browser_secret):
        with self.lock:
            pending = self.pending.pop(state, None)
        if not pending or pending[0] < time.monotonic() or not secrets.compare_digest(pending[1], browser_secret):
            raise ValueError("Autorização inválida ou expirada. Inicie novamente.")
        try:
            flow = self._flow(state=state, code_verifier=pending[2])
            flow.fetch_token(code=code, timeout=20)
            credentials = flow.credentials
            if not credentials.refresh_token or not credentials.has_scopes(SCOPES):
                raise CalendarError("Autorize a permissão de eventos e o acesso offline novamente.")
            with self.lock:
                self._save(credentials)
        except CalendarError:
            raise
        except Exception as exc:
            raise CalendarError("Não foi possível concluir a autorização Google.") from exc

    def _save(self, credentials):
        self.token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = self.cipher.encrypt(credentials.to_json().encode())
        fd, temp = tempfile.mkstemp(dir=self.token_path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
            os.replace(temp, self.token_path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    def _credentials(self):
        try:
            with self.lock:
                data = json.loads(self.cipher.decrypt(self.token_path.read_bytes()))
                credentials = Credentials.from_authorized_user_info(data, SCOPES)
                if not credentials.valid:
                    credentials.refresh(Request())
                    self._save(credentials)
                return credentials
        except FileNotFoundError as exc:
            logger.error(
                "Credenciais Google ausentes phase=credentials_load token_path=%s",
                self.token_path,
            )
            raise CalendarError("Conecte ou autorize novamente a agenda em /auth/google/connect.") from exc
        except Exception as exc:
            logger.exception(
                "Falha ao carregar ou renovar credenciais Google "
                "phase=credentials_load token_path=%s error_type=%s",
                self.token_path,
                type(exc).__name__,
            )
            raise CalendarError("Conecte ou autorize novamente a agenda em /auth/google/connect.") from exc

    def _request(self, method, event_id=None, **kwargs):
        url = "https://www.googleapis.com/calendar/v3/calendars/" + quote(self.calendar_id, safe="") + "/events"
        if event_id:
            url += "/" + quote(event_id, safe="")
        try:
            with AuthorizedSession(self._credentials()) as session:
                response = session.request(method, url, timeout=20, **kwargs)
            if not response.ok:
                logger.error(
                    "Google Calendar respondeu com erro phase=google_request "
                    "method=%s status=%s event_id=%s",
                    method,
                    response.status_code,
                    event_id or "none",
                )
            if method == "POST" and response.status_code == 409:
                existing = self._request("GET", kwargs["json"]["id"])
                if existing.get("extendedProperties", {}).get("private", {}).get("nailsflow_id") == kwargs["json"]["extendedProperties"]["private"]["nailsflow_id"]:
                    return existing
            if method == "DELETE" and response.status_code in (404, 410):
                return {}
            response.raise_for_status()
            return response.json() if response.content else {}
        except CalendarError:
            raise
        except Exception as exc:
            logger.exception(
                "Falha na requisição ao Google Calendar phase=google_request "
                "method=%s event_id=%s error_type=%s",
                method,
                event_id or "none",
                type(exc).__name__,
            )
            raise CalendarError("Falha ao acessar o Google Calendar. Tente novamente.") from exc

    @staticmethod
    def _body(appointment):
        from app.services.appointment_service import as_utc
        if appointment.client is None or appointment.service is None:
            raise CalendarError(
                "Não foi possível carregar a cliente e o serviço do agendamento para sincronizar a agenda."
            )
        return {
            "summary": f"💅 {appointment.service.name} - Cris Merlos",
            "description": (
            " ✨ Seu momento de cuidado está agendado! ✨\n\n"
            f"Serviço: {appointment.service.name}\n"
            f"Duração: {appointment.duration_minutes} minutos\n\n"
            "Confirme sua presença respondendo ao convite. 💌"
            "Esperamos você! 💕"
        ),
            "start": {"dateTime": as_utc(appointment.start_time).isoformat()},
            "end": {"dateTime": as_utc(appointment.end_time).isoformat()},
            "attendees": [{"email": str(appointment.client.email)}],
            "extendedProperties": {"private": {"nailsflow_id": appointment.id}},
        }

    def create_event(self, appointment):
        # UUID hexadecimal é um ID válido do Google; permite repetir sem duplicar.
        body = self._body(appointment)
        body["id"] = appointment.id.replace("-", "")
        return self._request("POST", json=body, params={"sendUpdates": "all"})["id"]

    def update_event(self, event_id, appointment):
        # PATCH preserva campos externos ao NailsFlow.
        body = self._body(appointment)
        current = self._request("GET", event_id)
        guests = current.get("attendees", [])
        if any(a.get("email", "").lower() == str(appointment.client.email).lower() for a in guests):
            body.pop("attendees")  # preserva a resposta ao convite já recebida
        self._request("PATCH", event_id, json=body, params={"sendUpdates": "all"})
        return True

    def delete_event(self, event_id):
        self._request("DELETE", event_id, params={"sendUpdates": "all"})
        return True

    def get_event_status(self, event_id):
        event = self._request("GET", event_id)
        if event.get("status") == "cancelled":
            return SyncStatus.REFUSED
        guests = [a for a in event.get("attendees", []) if not a.get("organizer")]
        status = guests[0].get("responseStatus") if guests else "needsAction"
        return {"accepted": SyncStatus.CONFIRMED, "declined": SyncStatus.REFUSED,
                "tentative": SyncStatus.MAYBE}.get(status, SyncStatus.PENDING)
