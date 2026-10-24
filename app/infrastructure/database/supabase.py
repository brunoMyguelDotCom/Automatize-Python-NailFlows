import json
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import ValidationError

from app.infrastructure.database.base import (
    BaseClientDatabase,
    BaseDatabase,
    ClientDatabaseError,
    AppointmentDatabaseError,
)
from app.domain.models import Appointment, ClientRecord
from app.core.logging_config import logger
from app.infrastructure.database.config import load_supabase_config


class SupabaseRestDatabase:
    record_model = ClientRecord
    database_error = ClientDatabaseError

    def _request(self, method: str, params=None, data=None):
        url = self.url
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = {
            "apikey": self.key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        # As chaves legadas são JWTs; chaves novas usam somente o header apikey.
        if self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                rows = json.load(response)
            if not isinstance(rows, list):
                raise ValueError("Expected a list of database records")
            return [self.record_model.model_validate(row) for row in rows]
        except HTTPError as exc:
            logger.error("Supabase request failed (HTTP %s)", exc.code)
            exc.close()
            raise self.database_error(
                "Falha ao acessar o banco de dados"
            ) from exc
        except (URLError, OSError, ValueError, ValidationError) as exc:
            logger.error("Supabase request failed (%s)", type(exc).__name__)
            raise self.database_error(
                "Falha ao acessar o banco de dados"
            ) from exc


class SupabaseClientDatabase(SupabaseRestDatabase, BaseClientDatabase):
    """Persistência de clientes pela API REST do Supabase."""

    def __init__(self, url: str, key: str):
        self.url = f"{url.rstrip('/')}/rest/v1/clients"
        self.key = key

    def create(self, client: ClientRecord) -> ClientRecord:
        rows = self._request("POST", data=client.model_dump(mode="json"))
        if not rows:
            raise ClientDatabaseError("O banco não retornou a cliente cadastrada")
        return rows[0]

    def get_by_id(self, client_id: str) -> Optional[ClientRecord]:
        rows = self._request(
            "GET", params={"id": f"eq.{client_id}", "select": "*", "limit": "1"}
        )
        return rows[0] if rows else None

    def list_all(self) -> List[ClientRecord]:
        return self._request(
            "GET", params={"select": "*", "order": "created_at.asc,id.asc"}
        )

    def update(
        self, client_id: str, updated_client: ClientRecord
    ) -> Optional[ClientRecord]:
        rows = self._request(
            "PATCH",
            params={"id": f"eq.{client_id}"},
            data=updated_client.model_dump(
                mode="json", include={"name", "email", "phone"}
            ),
        )
        return rows[0] if rows else None

    def delete(self, client_id: str) -> bool:
        rows = self._request("DELETE", params={"id": f"eq.{client_id}"})
        return bool(rows)


class SupabaseDatabase(SupabaseRestDatabase, BaseDatabase):
    """Persistência real dos agendamentos pela API REST do Supabase."""

    record_model = Appointment
    database_error = AppointmentDatabaseError

    def __init__(self, url=None, key=None):
        if url is None and key is None:
            url, key = load_supabase_config()
        self.url = f"{url.rstrip('/')}/rest/v1/appointments"
        self.key = key

    def create(self, appointment: Appointment) -> Appointment:
        rows = self._request(
            "POST", data=appointment.model_dump(mode="json", exclude={"end_time"})
        )
        if not rows:
            raise AppointmentDatabaseError("O banco não retornou o agendamento criado")
        return rows[0]

    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        rows = self._request(
            "GET", params={"id": f"eq.{appointment_id}", "select": "*", "limit": "1"}
        )
        return rows[0] if rows else None

    def list_all(self) -> List[Appointment]:
        return self._request("GET", params={"select": "*", "order": "start_time.asc,id.asc"})

    def update(self, appointment_id: str, updated_appointment: Appointment) -> Optional[Appointment]:
        rows = self._request(
            "PATCH", params={"id": f"eq.{appointment_id}"},
            data=updated_appointment.model_dump(mode="json", exclude={"id", "end_time"}),
        )
        return rows[0] if rows else None

    def delete(self, appointment_id: str) -> bool:
        return bool(self._request("DELETE", params={"id": f"eq.{appointment_id}"}))
