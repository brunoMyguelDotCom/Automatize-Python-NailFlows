from app.infrastructure.database.base import BaseDatabase
from app.domain.models import Appointment
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
