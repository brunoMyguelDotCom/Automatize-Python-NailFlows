from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import Appointment

class BaseDatabase(ABC):
    @abstractmethod
    def create(self, appointment: Appointment) -> Appointment:
        pass

    @abstractmethod
    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        pass

    @abstractmethod
    def list_all(self) -> List[Appointment]:
        pass

    @abstractmethod
    def update(self, appointment_id: str, updated_appointment: Appointment) -> Optional[Appointment]:
        pass

    @abstractmethod
    def delete(self, appointment_id: str) -> bool:
        pass
