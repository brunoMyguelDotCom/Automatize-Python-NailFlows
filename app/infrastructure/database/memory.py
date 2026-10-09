from app.infrastructure.database.base import BaseClientDatabase, BaseDatabase
from app.domain.models import Appointment, ClientRecord
from typing import List, Optional, Dict

class InMemoryDatabase(BaseDatabase):
    def __init__(self):
        self._storage: Dict[str, Appointment] = {}

    def create(self, appointment: Appointment) -> Appointment:
        self._storage[appointment.id] = appointment
        return appointment

    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        return self._storage.get(appointment_id)

    def list_all(self) -> List[Appointment]:
        return list(self._storage.values())

    def update(self, appointment_id: str, updated_appointment: Appointment) -> Optional[Appointment]:
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
        self._storage: Dict[str, ClientRecord] = {}

    def create(self, client: ClientRecord) -> ClientRecord:
        self._storage[client.id] = client
        return client

    def get_by_id(self, client_id: str) -> Optional[ClientRecord]:
        return self._storage.get(client_id)

    def list_all(self) -> List[ClientRecord]:
        return list(self._storage.values())

    def update(self, client_id: str, updated_client: ClientRecord) -> Optional[ClientRecord]:
        if client_id not in self._storage:
            return None
        self._storage[client_id] = updated_client
        return updated_client

    def delete(self, client_id: str) -> bool:
        return self._storage.pop(client_id, None) is not None
