import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from pydantic import ValidationError

from app.core.logging_config import logger
from app.domain.models import Appointment, ClientRecord, Service
from app.infrastructure.database.base import (
    AppointmentDatabaseError,
    BaseClientDatabase,
    BaseDatabase,
    BaseServiceDatabase,
    ClientDatabaseError,
    ForeignKeyViolationError,
    ServiceDatabaseError,
)
from app.infrastructure.database.config import load_supabase_config


class SupabaseRestDatabase:
    record_model = ClientRecord
    database_error = ClientDatabaseError

    def _request(self, method: str, params=None, data=None):
        url = self.url
        if params:
            # Use Resource Embedding for Appointment retrievals to fetch nested client and service data
            if self.record_model is Appointment and method == "GET":
                params = params or {}
                select_val = params.get("select", "*")
                # Ensure we select all appointment columns and the related client and service objects
                if "clients(*)" not in select_val or "services(*)" not in select_val:
                    if select_val == "*":
                        select_val = "*,clients(*),services(*)"
                    else:
                        select_val = f"{select_val},clients(*),services(*)"
                params["select"] = select_val

            url = f"{url}?{urlencode(params)}"
        headers = {
            "apikey": self.key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        if self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"

        def json_serial(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        body = (
            json.dumps(data, default=json_serial).encode("utf-8")
            if data is not None
            else None
        )
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=10) as response:
                rows = json.load(response)
            if not isinstance(rows, list):
                raise ValueError("Expected a list of database records")

            processed_rows = []
            for row in rows:
                if self.record_model is Appointment:
                    row = self._hydrate_appointment(row)
                processed_rows.append(row)

            return [self.record_model.model_validate(row) for row in processed_rows]
        except HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8")
                logger.error("Supabase HTTP Error %s: %s", exc.code, error_body)

                if (
                    "foreign_key_violation" in error_body
                    or "violates foreign key constraint" in error_body
                    or "23503" in error_body
                ):
                    raise ForeignKeyViolationError(
                        "Violação de chave estrangeira detectada no banco de dados"
                    ) from exc
            except ForeignKeyViolationError:
                raise
            except Exception as read_exc:
                logger.error("Could not read Supabase error body: %s", str(read_exc))

            exc.close()
            # Use the record_model's specific database_error to avoid generic errors
            raise self.database_error("Falha ao acessar o banco de dados") from exc
        except (URLError, OSError, ValueError, ValidationError) as exc:
            logger.error("Supabase request failed (%s)", type(exc).__name__)
            raise self.database_error("Falha ao acessar o banco de dados") from exc

    def _hydrate_appointment(self, row: dict) -> dict:
        """Reconstructs nested Appointment models from flat database columns and joined client/service data."""
        client_data = row.pop("clients", None)
        if isinstance(client_data, dict):
            row["client"] = client_data
        elif isinstance(client_data, list) and client_data:
            row["client"] = client_data[0]
        else:
            row["client"] = None

        service_data = row.pop("services", None)
        if isinstance(service_data, dict):
            row["service"] = service_data
        elif isinstance(service_data, list) and service_data:
            row["service"] = service_data[0]
        else:
            row["service"] = None

        row["sync_state"] = {
            "google_event_id": row.pop("sync_google_event_id", None),
            "status": row.pop("sync_status", "Pending"),
            "last_synced": row.pop("sync_last_synced", None),
        }
        return row


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

    def get_by_id(self, client_id: str) -> ClientRecord | None:
        rows = self._request(
            "GET", params={"id": f"eq.{client_id}", "select": "*", "limit": "1"}
        )
        return rows[0] if rows else None

    def list_all(self) -> list[ClientRecord]:
        return self._request(
            "GET", params={"select": "*", "order": "created_at.asc,id.asc"}
        )

    def update(
        self, client_id: str, updated_client: ClientRecord
    ) -> ClientRecord | None:
        rows = self._request(
            "PATCH",
            params={"id": f"eq.{client_id}"},
            data=updated_client.model_dump(
                mode="json", include={"name", "email", "phone"}
            ),
        )
        return rows[0] if rows else None

    def delete(self, client_id: str) -> bool:
        try:
            rows = self._request("DELETE", params={"id": f"eq.{client_id}"})
            return bool(rows)
        except self.database_error as exc:
            logger.error("Falha ao deletar cliente %s: %s", client_id, str(exc))
            raise


class SupabaseServiceDatabase(SupabaseRestDatabase, BaseServiceDatabase):
    """Persistência de serviços pela API REST do Supabase."""

    def __init__(self, url: str, key: str):
        self.url = f"{url.rstrip('/')}/rest/v1/services"
        self.key = key
        self.record_model = Service
        self.database_error = ServiceDatabaseError

    def create(self, service: Service) -> Service:
        rows = self._request("POST", data=service.model_dump(mode="json"))
        if not rows:
            raise ServiceDatabaseError("O banco não retornou o serviço cadastrado")
        return rows[0]

    def get_by_id(self, service_id: str) -> Service | None:
        rows = self._request(
            "GET", params={"id": f"eq.{service_id}", "select": "*", "limit": "1"}
        )
        return rows[0] if rows else None

    def list_all(self) -> list[Service]:
        return self._request("GET", params={"select": "*", "order": "name.asc,id.asc"})

    def update(self, service_id: str, updated_service: Service) -> Service | None:
        rows = self._request(
            "PATCH",
            params={"id": f"eq.{service_id}"},
            data=updated_service.model_dump(mode="json"),
        )
        return rows[0] if rows else None

    def delete(self, service_id: str) -> bool:
        try:
            rows = self._request("DELETE", params={"id": f"eq.{service_id}"})
            return bool(rows)
        except self.database_error as exc:
            logger.error("Falha ao deletar serviço %s: %s", service_id, str(exc))
            raise


class SupabaseDatabase(SupabaseRestDatabase, BaseDatabase):
    """Persistência real dos agendamentos pela API REST do Supabase."""

    record_model = Appointment
    database_error = AppointmentDatabaseError

    def __init__(self, url=None, key=None):
        if url is None and key is None:
            url, key = load_supabase_config()
        self.url = f"{url.rstrip('/')}/rest/v1/appointments"
        self.key = key

    def _flatten_appointment(
        self, appointment: Appointment, partial: bool = False
    ) -> dict:
        """Converts a structured Appointment domain model into a flat dictionary for the DB.
        Only includes columns that actually exist in the PostgreSQL table.
        """
        # Construct the data dictionary explicitly to avoid sending 'service' or other non-existent columns
        data = {
            "start_time": appointment.start_time.isoformat()
            if hasattr(appointment.start_time, "isoformat")
            else appointment.start_time,
            "duration_minutes": appointment.duration_minutes,
            "client_id": appointment.client_id,
            "service_id": appointment.service_id,
            "sync_google_event_id": appointment.sync_state.google_event_id,
            "sync_status": appointment.sync_state.status.value,
            "sync_last_synced": appointment.sync_state.last_synced.isoformat()
            if appointment.sync_state.last_synced
            else None,
        }

        if partial:
            # For updates, we only send fields that were explicitly changed.
            # Since we are using the domain model here, we rely on the service layer
            # to pass the updated object. To be safe, we keep the explicit map.
            pass

        return data

    def create(self, appointment: Appointment) -> Appointment:
        rows = self._request("POST", data=self._flatten_appointment(appointment))
        if not rows:
            raise AppointmentDatabaseError("O banco não retornou o agendamento criado")
        return rows[0]

    def get_by_id(self, appointment_id: str) -> Appointment | None:
        rows = self._request(
            "GET", params={"id": f"eq.{appointment_id}", "select": "*", "limit": "1"}
        )
        return rows[0] if rows else None

    def list_all(self) -> list[Appointment]:
        return self._request(
            "GET", params={"select": "*", "order": "start_time.asc,id.asc"}
        )

    def update(
        self, appointment_id: str, updated_appointment: Appointment
    ) -> Appointment | None:
        rows = self._request(
            "PATCH",
            params={"id": f"eq.{appointment_id}"},
            data=self._flatten_appointment(updated_appointment, partial=True),
        )
        return rows[0] if rows else None

    def delete(self, appointment_id: str) -> bool:
        return bool(self._request("DELETE", params={"id": f"eq.{appointment_id}"}))
