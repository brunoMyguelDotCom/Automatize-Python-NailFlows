import os
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
)
from app.domain.models import Appointment, ClientRecord
from app.core.logging_config import logger


class SupabaseDatabase(BaseDatabase):
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        # In a real implementation, we would initialize the supabase-py client here
        # self.client = create_client(self.url, self.key)

    def create(self, appointment: Appointment) -> Appointment:
        logger.info(f"Creating appointment {appointment.id} in Supabase...")
        # self.client.table('appointments').insert(appointment.dict()).execute()
        return appointment

    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        logger.info(f"Getting appointment {appointment_id} from Supabase...")
        return None

    def list_all(self) -> List[Appointment]:
        logger.info("Listing all appointments from Supabase...")
        return []

    def update(
        self, appointment_id: str, updated_appointment: Appointment
    ) -> Optional[Appointment]:
        logger.info(f"Updating appointment {appointment_id} in Supabase...")
        return updated_appointment

    def delete(self, appointment_id: str) -> bool:
        logger.info(f"Deleting appointment {appointment_id} from Supabase...")
        return True


class SupabaseClientDatabase(BaseClientDatabase):
    """Persistência de clientes pela API REST do Supabase."""

    def __init__(self, url: str, key: str):
        self.url = f"{url.rstrip('/')}/rest/v1/clients"
        self.key = key

    def _request(self, method: str, params=None, data=None) -> List[ClientRecord]:
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
                raise ValueError("Expected a list of client records")
            return [ClientRecord.model_validate(row) for row in rows]
        except HTTPError as exc:
            logger.error("Supabase client request failed (HTTP %s)", exc.code)
            exc.close()
            raise ClientDatabaseError(
                "Falha ao acessar o cadastro de clientes"
            ) from exc
        except (URLError, OSError, ValueError, ValidationError) as exc:
            logger.error("Supabase client request failed (%s)", type(exc).__name__)
            raise ClientDatabaseError(
                "Falha ao acessar o cadastro de clientes"
            ) from exc

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
