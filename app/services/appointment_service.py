from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Optional, Union
from fastapi import HTTPException

from app.domain.models import Appointment, SyncStatus, AppointmentCreate
from app.infrastructure.database.base import BaseDatabase, AppointmentDatabaseError, ForeignKeyViolationError, BaseServiceDatabase
from app.infrastructure.calendar.base import BaseCalendar

def as_utc(value: datetime) -> datetime:
    # Datas sem fuso da API são interpretadas no horário de São Paulo.
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
    return value.astimezone(timezone.utc)


class AppointmentService:
    def __init__(self, db: BaseDatabase, calendar: BaseCalendar, service_db: Optional[BaseServiceDatabase] = None):
        self.db = db
        self.calendar = calendar
        self.service_db = service_db

    def _validate_appointment(
        self, appointment: Appointment, ignore_id: Optional[str] = None
    ):
        # 1. Prevent appointments in the past
        if as_utc(appointment.start_time) < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400, detail="Appointment cannot be in the past"
            )

        # 2. Prevent overlapping appointments
        all_appointments = self.db.list_all()
        for existing in all_appointments:
            if ignore_id and existing.id == ignore_id:
                continue

            # Check for overlap: (StartA < EndB) and (EndA > StartB)
            if (
                as_utc(appointment.start_time) < as_utc(existing.end_time)
                and as_utc(appointment.end_time) > as_utc(existing.start_time)
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"Appointment overlaps with an existing one (ID: {existing.id})",
                )

    def create_appointment(self, appointment_data: AppointmentCreate) -> Appointment:
        # Validate if the service is active and get its default duration
        default_duration = None
        if self.service_db:
            service = self.service_db.get_by_id(appointment_data.service_id)
            if service is None:
                raise HTTPException(
                    status_code=400, detail="O serviço informado não existe no sistema"
                )
            if not service.active:
                raise HTTPException(
                    status_code=400, detail="O serviço selecionado está inativo e não pode ser utilizado para novos agendamentos"
                )
            default_duration = service.duration_minutes

        # Logic for duration: use provided value or fall back to service default
        final_duration = appointment_data.duration_minutes
        if final_duration is None:
            if default_duration is None:
                raise HTTPException(
                    status_code=400, detail="Duração não informada e serviço não possui duração padrão"
                )
            final_duration = default_duration

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
                raise AppointmentDatabaseError("Agendamento não encontrado ao salvar sincronização")
            appointment = saved

        # IMPORTANT: Hydrate the final object before returning to ensure client and service data are present
        return self.get_appointment(appointment.id)

    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        return self.db.get_by_id(appointment_id)

    def list_appointments(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Appointment]:
        appointments = self.db.list_all()

        # Filter by date range
        if start_date:
            appointments = [a for a in appointments if as_utc(a.start_time) >= as_utc(start_date)]
        if end_date:
            appointments = [a for a in appointments if as_utc(a.start_time) <= as_utc(end_date)]

        # Sort by start_time ascending
        appointments.sort(key=lambda x: as_utc(x.start_time))

        return appointments

    def update_appointment(
        self, appointment_id: str, updated_data: AppointmentCreate
    ) -> Appointment:
        # Fetch existing to maintain sync_state if not provided or to merge
        existing = self.get_appointment(appointment_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Validate if the service is active and get its default duration
        default_duration = None
        if self.service_db:
            service = self.service_db.get_by_id(updated_data.service_id)
            if service is None:
                raise HTTPException(
                    status_code=400, detail="O serviço informado não existe no sistema"
                )
            if not service.active:
                raise HTTPException(
                    status_code=400, detail="O serviço selecionado está inativo e não pode ser utilizado para novos agendamentos"
                )
            default_duration = service.duration_minutes

        # Logic for duration: use provided value or fall back to service default
        final_duration = updated_data.duration_minutes
        if final_duration is None:
            if default_duration is None:
                raise HTTPException(
                    status_code=400, detail="Duração não informada e serviço não possui duração padrão"
                )
            final_duration = default_duration

        # Create Appointment model with the existing ID
        updated_appointment = Appointment(**updated_data.model_dump())
        updated_appointment.id = appointment_id
        updated_appointment.duration_minutes = final_duration
        updated_appointment.start_time = as_utc(updated_appointment.start_time)

        self._validate_appointment(updated_appointment, ignore_id=appointment_id)

        # Save to DB
        try:
            saved = self.db.update(appointment_id, updated_appointment)
        except ForeignKeyViolationError:
            raise HTTPException(
                status_code=400, detail="O cliente informado não existe no sistema"
            )

        if saved is None:
            raise HTTPException(status_code=404, detail="Appointment not found")
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
        Em vez de remover do banco, define o agendamento como inativo.
        """
        try:
            appointment = self.get_appointment(appointment_id)
            if not appointment:
                return False

            # Remove from Google Calendar if it exists
            if appointment.sync_state.google_event_id:
                self.calendar.delete_event(appointment.sync_state.google_event_id)

            # Update as inactive
            updated_appointment = Appointment(**appointment.model_dump())
            updated_appointment.active = False

            return self.db.update(appointment_id, updated_appointment) is not None
        except Exception as e:
            logger.error("Erro inesperado ao cancelar agendamento: %s", str(e))
            raise HTTPException(status_code=503, detail="Falha ao acessar o banco de dados")

    def synchronize_status(self, appointment_id: str) -> Appointment:
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        event_id = appointment.sync_state.google_event_id
        if not event_id:
            raise HTTPException(
                status_code=400,
                detail="No Google Event ID associated with this appointment",
            )

        # Poll Google Calendar for status
        new_status = self.calendar.get_event_status(event_id)
        if new_status:
            appointment.sync_state.status = new_status
            saved = self.db.update(appointment.id, appointment)
            if saved is None:
                raise AppointmentDatabaseError("Agendamento não encontrado ao salvar sincronização")
            appointment = saved

        return appointment
