import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
)


class SyncStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    REFUSED = "Refused"
    MAYBE = "Maybe"


class Client(BaseModel):
    name: str = Field(
        ..., description="Nome completo da cliente", example="Maria Silva"
    )
    email: EmailStr = Field(
        ..., description="Endereço de email da cliente", example="maria@email.com"
    )
    phone: str | None = Field(
        None, description="Telefone de contato da cliente", example="+55 11 99999-9999"
    )


class ClientCreate(Client):
    """Dados enviados para cadastrar uma cliente."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(
        ...,
        min_length=1,
        description="Nome completo da cliente",
        examples=["Maria Silva"],
    )
    phone: str = Field(
        ...,
        min_length=1,
        description="Número de telefone/WhatsApp da cliente",
        examples=["+55 11 99999-9999"],
    )


class ClientUpdate(BaseModel):
    """Campos opcionais para atualização parcial; campos enviados não podem ser nulos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(
        None,
        min_length=1,
        description="Nome completo da cliente",
        examples=["Maria Silva"],
    )
    email: EmailStr | None = Field(
        None, description="Endereço de e-mail da cliente", examples=["maria@email.com"]
    )
    phone: str | None = Field(
        None,
        min_length=1,
        description="Número de telefone/WhatsApp da cliente",
        examples=["+55 11 99999-9999"],
    )

    @field_validator("name", "email", "phone")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError(
                "O campo não pode ser nulo; omita-o para manter o valor atual"
            )
        return value


class ClientRecord(ClientCreate):
    """Cliente cadastrada, com identificação e data geradas pelo servidor."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único da cliente",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Data e hora do cadastro em UTC",
        examples=["2026-10-09T15:00:00Z"],
    )


class SyncState(BaseModel):
    google_event_id: str | None = Field(
        None, description="ID do evento no Google Calendar", example="ev_123456789"
    )
    status: SyncStatus = Field(
        SyncStatus.PENDING,
        description="Status atual de sincronização/confirmação",
        example=SyncStatus.PENDING,
    )
    last_synced: datetime | None = Field(
        None, description="Data e hora da última sincronização"
    )


class Service(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único do serviço",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    name: str = Field(..., description="Nome do serviço", example="Alongamento em Gel")
    duration_minutes: int = Field(
        ..., description="Duração do serviço em minutos", example=120
    )
    active: bool = Field(default=True, description="Indica se o serviço está ativo")


class ServiceCreate(BaseModel):
    """Dados enviados para cadastrar um serviço."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(..., min_length=1, description="Nome do serviço")
    duration_minutes: int = Field(..., gt=0, description="Duração em minutos")
    active: bool = Field(default=True, description="Status do serviço")


class ServiceUpdate(BaseModel):
    """Campos opcionais para atualização de serviço."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str | None = Field(None, min_length=1)
    duration_minutes: int | None = Field(None, gt=0)
    active: bool | None = None


class AppointmentBase(BaseModel):
    service_id: str = Field(
        ...,
        description="ID do serviço vinculado ao agendamento",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    start_time: datetime = Field(
        ...,
        description="Data e hora de início do agendamento (deve ser data futura)",
        example="2026-11-10T14:00:00",
    )
    duration_minutes: int | None = Field(
        None,
        description="Duração do serviço em minutos. Se omitido, usa a duração padrão do serviço.",
        example=120,
    )


class AppointmentCreate(AppointmentBase):
    """Modelo para criação de agendamento. O ID e o cliente são obrigatórios."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    client_id: str = Field(
        ...,
        description="ID da cliente vinculada ao agendamento",
        example="550e8400-e29b-41d4-a716-446655440000",
    )


class Appointment(AppointmentBase):
    """Modelo completo de agendamento, incluindo o ID e a cliente hidratada."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Identificador único do agendamento",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    client_id: str = Field(..., description="ID da cliente vinculada")
    service_id: str = Field(..., description="ID do serviço vinculado")
    sync_state: SyncState = Field(
        default_factory=SyncState,
        description="Estado de sincronização com o calendário",
    )
    active: bool = Field(
        default=True, description="Indica se o agendamento está ativo ou foi cancelador"
    )
    client: Client | None = Field(
        default=None, description="Dados da cliente (carregados via join)"
    )
    service: Service | None = Field(
        default=None, description="Dados do serviço (carregados via join)"
    )

    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration_minutes)
