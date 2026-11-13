from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from app.domain.models import Appointment, AppointmentCreate
from app.infrastructure.calendar.base import BaseCalendar
from app.infrastructure.database.base import (
    AppointmentDatabaseError,
    BaseDatabase,
    BaseServiceDatabase,
    ForeignKeyViolationError,
)
from app.core.logging_config import logger


def as_utc(value: datetime) -> datetime:
    # Datas sem fuso da API são interpretadas no horário de São Paulo.
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
    return value.astimezone(UTC)


class AppointmentService:
    def __init__(
        self,
        db: BaseDatabase,
        calendar: BaseCalendar,
        service_db: BaseServiceDatabase | None = None,
    ):
        self.db = db
        self.calendar = calendar
        self.service_db = service_db

    def _resolve_service_duration(
        self, service_id: str, provided_duration: int | None
    ) -> int:
        """
        Valida se o serviço está ativo e resolve a duração final:
        1. Se o usuário forneceu a duração, usa ela.
        2. Se não, usa a duração padrão do serviço.
        """
        if not self.service_db:
            if provided_duration is not None:
                return provided_duration
            raise HTTPException(
                status_code=500,
                detail="Banco de serviços não configurado para validar a duração",
            )

        service = self.service_db.get_by_id(service_id)
        if service is None:
            raise HTTPException(
                status_code=400, detail="O serviço informado não existe no sistema"
            )
        if not service.active:
            raise HTTPException(
                status_code=400,
                detail="O serviço selecionado está inativo e não pode ser utilizado para novos agendamentos",
            )

        return (
            provided_duration
            if provided_duration is not None
            else service.duration_minutes
        )

    def _validate_appointment(
        self, appointment: Appointment, ignore_id: str | None = None
    ):
        # 1. Impedir agendamentos no passado
        if as_utc(appointment.start_time) < datetime.now(UTC):
            raise HTTPException(
                status_code=400, detail="O agendamento não pode ser em uma data passada"
            )

        # 2. Impedir sobreposição de horários
        all_appointments = self.db.list_all()
        for existing in all_appointments:
            if ignore_id and existing.id == ignore_id:
                continue

            # Check for overlap: (StartA < EndB) and (EndA > StartB)
            if as_utc(appointment.start_time) < as_utc(existing.end_time) and as_utc(
                appointment.end_time
            ) > as_utc(existing.start_time):
                raise HTTPException(
                    status_code=400,
                    detail=f"Este horário coincide com um agendamento já existente (ID: {existing.id})",
                )

    def create_appointment(self, appointment_data: AppointmentCreate) -> Appointment:
        # Resolve duração e valida serviço
        final_duration = self._resolve_service_duration(
            appointment_data.service_id, appointment_data.duration_minutes
        )

        # Convert AppointmentCreate to Appointment to generate ID
        appointment = Appointment(**appointment_data.model_dump())
        appointment.duration_minutes = final_duration
        appointment.start_time = as_utc(appointment.start_time)
        self._validate_appointment(appointment)

        # Save to DB
        try:
            appointment = self.db.create(appointment)
        except ForeignKeyViolationError:
            raise HTTPException(
                status_code=400, detail="O cliente informado não existe no sistema"
            )

        # Sync with Google Calendar
        event_id = self.calendar.create_event(appointment)
        if event_id:
            appointment.sync_state.google_event_id = event_id
            saved = self.db.update(appointment.id, appointment)
            if saved is None:
                raise AppointmentDatabaseError(
                    "Agendamento não encontrado ao salvar sincronização"
                )
            appointment = saved

        return self.get_appointment(appointment.id)

    def get_appointment(self, appointment_id: str) -> Appointment | None:
        return self.db.get_by_id(appointment_id)

    def list_appointments(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        active_only: bool = False,
    ) -> list[Appointment]:
        appointments = self.db.list_all()

        # Filter by active status if requested
        if active_only:
            appointments = [a for a in appointments if a.active]

        # Filter by date range
        if start_date:
            appointments = [
                a for a in appointments if as_utc(a.start_time) >= as_utc(start_date)
            ]
        if end_date:
            appointments = [
                a for a in appointments if as_utc(a.start_time) <= as_utc(end_date)
            ]

        # Sort by start_time ascending
        appointments.sort(key=lambda x: as_utc(x.start_time))

        return appointments

    def update_appointment(
        self, appointment_id: str, updated_data: AppointmentCreate
    ) -> Appointment:
        # Fetch existing to maintain sync_state if not provided or to merge
        existing = self.get_appointment(appointment_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")

        # Resolve duração e valida serviço
        final_duration = self._resolve_service_duration(
            updated_data.service_id, updated_data.duration_minutes
        )

        # Create Appointment model with the existing ID
        updated_appointment = Appointment(**updated_data.model_dump())
        updated_appointment.duration_minutes = final_duration
        updated_appointment.id = appointment_id
        updated_appointment.start_time = as_utc(updated_appointment.start_time)

        # Maintain sync state from existing
        updated_appointment.sync_state = existing.sync_state

        self._validate_appointment(updated_appointment, ignore_id=appointment_id)

        # Save to DB
        try:
            saved = self.db.update(appointment_id, updated_appointment)
        except ForeignKeyViolationError:
            raise HTTPException(
                status_code=400, detail="O cliente informado não existe no sistema"
            )

        if saved is None:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")
        updated_appointment = saved

        # Sync with Google Calendar
        if updated_appointment.sync_state.google_event_id:
            self.calendar.update_event(
                updated_appointment.sync_state.google_event_id, updated_appointment
            )

        return self.get_appointment(updated_appointment.id)

    def cancel_appointment(self, appointment_id: str) -> bool:
        """
        Implementa a deleção lógica (soft delete).
        """
        try:
            appointment = self.get_appointment(appointment_id)
        except Exception:
            logger.exception(
                "Falha ao carregar agendamento para cancelamento "
                "phase=database_read appointment_id=%s",
                appointment_id,
            )
            raise HTTPException(
                status_code=503, detail="Falha ao acessar o banco de dados"
            )

        if not appointment:
            logger.warning(
                "Agendamento não encontrado para cancelamento appointment_id=%s",
                appointment_id,
            )
            return False

        google_event_id = appointment.sync_state.google_event_id
        if google_event_id:
            try:
                self.calendar.delete_event(google_event_id)
            except Exception:
                logger.exception(
                    "Falha ao excluir evento do Google "
                    "phase=google_delete appointment_id=%s google_event_id=%s",
                    appointment_id,
                    google_event_id,
                )
                raise HTTPException(
                    status_code=503,
                    detail="Falha ao cancelar o evento no Google Calendar",
                )

        updated_appointment = Appointment(**appointment.model_dump())
        updated_appointment.active = False
        try:
            saved = self.db.update(appointment_id, updated_appointment)
        except Exception:
            logger.exception(
                "Falha ao atualizar status do agendamento "
                "phase=database_update appointment_id=%s active=false",
                appointment_id,
            )
            raise HTTPException(
                status_code=503, detail="Falha ao acessar o banco de dados"
            )

        logger.info(
            "Agendamento cancelado phase=completed appointment_id=%s active=false "
            "google_event_id_present=%s",
            appointment_id,
            bool(google_event_id),
        )
        return saved is not None

    def synchronize_status(self, appointment_id: str) -> Appointment:
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Agendamento não encontrado")

        event_id = appointment.sync_state.google_event_id
        if not event_id:
            raise HTTPException(
                status_code=400,
                detail="No Google Event ID associated with this appointment",
            )

        new_status = self.calendar.get_event_status(event_id)
        if new_status:
            appointment.sync_state.status = new_status
            appointment.sync_state.last_synced = datetime.now(UTC)
            saved = self.db.update(appointment.id, appointment)
            if saved is None:
                raise AppointmentDatabaseError(
                    "Agendamento não encontrado ao salvar sincronização"
                )
            appointment = saved

        return appointment
