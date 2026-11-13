from threading import RLock
from app.domain.models import (
    Appointment, ClientRecord, DuplicateClientError, client_email_key, client_phone_key,
)
from app.infrastructure.database.base import BaseClientDatabase, BaseDatabase


class InMemoryDatabase(BaseDatabase):
    def __init__(self):
        self._storage: dict[str, Appointment] = {}

    def create(self, appointment: Appointment) -> Appointment:
        self._storage[appointment.id] = appointment
        return appointment

    def get_by_id(self, appointment_id: str) -> Appointment | None:
        return self._storage.get(appointment_id)

    def list_all(self) -> list[Appointment]:
        return list(self._storage.values())

    def update(
        self, appointment_id: str, updated_appointment: Appointment
    ) -> Appointment | None:
        if appointment_id in self._storage:
            self._storage[appointment_id] = updated_appointment
            return updated_appointment
        return None

    def delete(self, appointment_id: str) -> bool:
        if appointment_id in self._storage:
            del self._storage[appointment_id]
            return True
        return False


class InMemoryClientDatabase(BaseClientDatabase):
    def __init__(self):
        self._storage: dict[str, ClientRecord] = {}
        self._lock = RLock()

    def _check_duplicates(self, client, exclude_id=None):
        for existing in self._storage.values():
            if existing.id == exclude_id:
                continue
            if client_email_key(existing.email) == client_email_key(client.email):
                raise DuplicateClientError("email")
            if client_phone_key(existing.phone) == client_phone_key(client.phone):
                raise DuplicateClientError("phone")

    def create(self, client: ClientRecord) -> ClientRecord:
        with self._lock:
            self._check_duplicates(client)
            self._storage[client.id] = client
            return client

    def get_by_id(self, client_id: str) -> ClientRecord | None:
        return self._storage.get(client_id)

    def list_all(self) -> list[ClientRecord]:
        with self._lock:
            return list(self._storage.values())

    def update(
        self, client_id: str, updated_client: ClientRecord
    ) -> ClientRecord | None:
        with self._lock:
            if client_id not in self._storage:
                return None
            self._check_duplicates(updated_client, exclude_id=client_id)
            self._storage[client_id] = updated_client
            return updated_client

    def delete(self, client_id: str) -> bool:
        with self._lock:
            return self._storage.pop(client_id, None) is not None
