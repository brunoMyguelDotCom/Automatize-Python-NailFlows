from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException

from app.domain.models import Appointment, SyncStatus
from app.infrastructure.database.base import BaseDatabase
from app.infrastructure.calendar.base import BaseCalendar

class AppointmentService:
    def __init__(self, db: BaseDatabase, calendar: BaseCalendar):
        self.db = db
        self.calendar = calendar

    def _validate_appointment(self, appointment: Appointment, ignore_id: Optional[str] = None):
        # 1. Prevent appointments in the past
        if appointment.start_time < datetime.now():
            raise HTTPException(status_code=400, detail="Appointment cannot be in the past")

        # 2. Prevent overlapping appointments
        all_appointments = self.db.list_all()
        for existing in all_appointments:
            if ignore_id and existing.id == ignore_id:
                continue

            # Check for overlap: (StartA < EndB) and (EndA > StartB)
            if appointment.start_time < existing.end_time and appointment.end_time > existing.start_time:
                raise HTTPException(
                    status_code=400,
                    detail=f"Appointment overlaps with an existing one (ID: {existing.id})"
                )

    def create_appointment(self, appointment: Appointment) -> Appointment:
        self._validate_appointment(appointment)

        # Save to DB
        self.db.create(appointment)

        # Sync with Google Calendar
        event_id = self.calendar.create_event(appointment)
        if event_id:
            appointment.sync_state.google_event_id = event_id
            self.db.update(appointment.id, appointment)

        return appointment

    def get_appointment(self, appointment_id: str) -> Optional[Appointment]:
        return self.db.get_by_id(appointment_id)

    def list_appointments(self) -> List[Appointment]:
        return self.db.list_all()

    def update_appointment(self, appointment_id: str, updated_appointment: Appointment) -> Appointment:
        # Update the ID to match the existing one
        updated_appointment.id = appointment_id
        self._validate_appointment(updated_appointment, ignore_id=appointment_id)

        # Save to DB
        self.db.update(appointment_id, updated_appointment)

        # Sync with Google Calendar
        if updated_appointment.sync_state.google_event_id:
            self.calendar.update_event(
                updated_appointment.sync_state.google_event_id,
                updated_appointment
            )

        return updated_appointment

    def cancel_appointment(self, appointment_id: str) -> bool:
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            return False

        # Remove from Google Calendar
        if appointment.sync_state.google_event_id:
            self.calendar.delete_event(appointment.sync_state.google_event_id)

        return self.db.delete(appointment_id)

    def synchronize_status(self, appointment_id: str) -> Appointment:
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        event_id = appointment.sync_state.google_event_id
        if not event_id:
            raise HTTPException(status_code=400, detail="No Google Event ID associated with this appointment")

        # Poll Google Calendar for status
        new_status = self.calendar.get_event_status(event_id)
        if new_status:
            appointment.sync_state.status = new_status
            self.db.update(appointment.id, appointment)

        return appointment
