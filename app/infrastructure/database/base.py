from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import Appointment, ClientRecord, Service


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
    def update(
        self, appointment_id: str, updated_appointment: Appointment
    ) -> Optional[Appointment]:
        pass

    @abstractmethod
    def delete(self, appointment_id: str) -> bool:
        pass


class ClientDatabaseError(RuntimeError):
    """Falha de acesso ao armazenamento de clientes."""

class AppointmentDatabaseError(RuntimeError):
    """Falha de acesso ao armazenamento de agendamentos."""

class ForeignKeyViolationError(RuntimeError):
    """Erro de violação de chave estrangeira (ex: cliente inexistente ou vinculado)."""


class BaseClientDatabase(ABC):
    @abstractmethod
    def create(self, client: ClientRecord) -> ClientRecord:
        pass

    @abstractmethod
    def get_by_id(self, client_id: str) -> Optional[ClientRecord]:
        pass

    @abstractmethod
    def list_all(self) -> List[ClientRecord]:
        pass

    @abstractmethod
    def update(
        self, client_id: str, updated_client: ClientRecord
    ) -> Optional[ClientRecord]:
        pass

    @abstractmethod
    def delete(self, client_id: str) -> bool:
        pass


class BaseServiceDatabase(ABC):
    @abstractmethod
    def create(self, service: Service) -> Service:
        pass

    @abstractmethod
    def get_by_id(self, service_id: str) -> Optional[Service]:
        pass

    @abstractmethod
    def list_all(self) -> List[Service]:
        pass

    @abstractmethod
    def update(
        self, service_id: str, updated_service: Service
    ) -> Optional[Service]:
        pass

    @abstractmethod
    def delete(self, service_id: str) -> bool:
        pass

class ServiceDatabaseError(RuntimeError):
    """Falha de acesso ao armazenamento de serviços."""
