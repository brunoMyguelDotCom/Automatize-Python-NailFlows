from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid

class SyncStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    REFUSED = "Refused"
    MAYBE = "Maybe"

class Client(BaseModel):
    name: str = Field(..., description="Nome completo da cliente", example="Maria Silva")
    email: EmailStr = Field(..., description="Endereço de email da cliente", example="maria@email.com")
    phone: Optional[str] = Field(None, description="Telefone de contato da cliente", example="+55 11 99999-9999")

class ClientCreate(Client):
    """Dados enviados para cadastrar uma cliente."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, description="Nome completo da cliente", examples=["Maria Silva"])
    phone: str = Field(..., min_length=1, description="Número de telefone/WhatsApp da cliente", examples=["+55 11 99999-9999"])

class ClientUpdate(BaseModel):
    """Campos opcionais para atualização parcial; campos enviados não podem ser nulos."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, description="Nome completo da cliente", examples=["Maria Silva"])
    email: Optional[EmailStr] = Field(None, description="Endereço de e-mail da cliente", examples=["maria@email.com"])
    phone: Optional[str] = Field(None, min_length=1, description="Número de telefone/WhatsApp da cliente", examples=["+55 11 99999-9999"])

    @field_validator("name", "email", "phone")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo; omita-o para manter o valor atual")
        return value

class ClientRecord(ClientCreate):
    """Cliente cadastrada, com identificação e data geradas pelo servidor."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador único da cliente", examples=["550e8400-e29b-41d4-a716-446655440000"])
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Data e hora do cadastro em UTC", examples=["2026-10-09T15:00:00Z"])

class SyncState(BaseModel):
    google_event_id: Optional[str] = Field(None, description="ID do evento no Google Calendar", example="ev_123456789")
    status: SyncStatus = Field(SyncStatus.PENDING, description="Status atual de sincronização/confirmação", example=SyncStatus.PENDING)
    last_synced: Optional[datetime] = Field(None, description="Data e hora da última sincronização")

class AppointmentBase(BaseModel):
    client: Client = Field(..., description="Dados da cliente")
    service: str = Field(..., description="Nome do serviço a ser realizado", example="Alongamento em Gel")
    start_time: datetime = Field(..., description="Data e hora de início do agendamento", example="2026-10-20T14:00:00")
    duration_minutes: int = Field(..., description="Duração do serviço em minutos", example=120)
    sync_state: SyncState = Field(default_factory=SyncState, description="Estado de sincronização com o calendário")

class AppointmentCreate(AppointmentBase):
    """Modelo para criação de agendamento. O ID é gerado automaticamente."""
    pass

class Appointment(AppointmentBase):
    """Modelo completo de agendamento, incluindo o ID gerado."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Identificador único do agendamento", example="550e8400-e29b-41d4-a716-446655440000")

    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration_minutes)
