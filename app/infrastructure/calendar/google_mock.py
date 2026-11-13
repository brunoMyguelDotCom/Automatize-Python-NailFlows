import random
import uuid

from app.core.logging_config import logger
from app.domain.models import Appointment, SyncStatus
from app.infrastructure.calendar.base import BaseCalendar


class GoogleMockCalendar(BaseCalendar):
    def __init__(self):
        # Mocking event storage: event_id -> (appointment_data, status)
        self._events: dict[str, tuple] = {}

    def create_event(self, appointment: Appointment) -> str | None:
        event_id = f"google_{uuid.uuid4().hex[:8]}"
        # Mocking that Google creates the event with PENDING status
        self._events[event_id] = (appointment, SyncStatus.PENDING)

        # Use client_id because the client object is not hydrated during creation
        client_label = (
            appointment.client.name if appointment.client else appointment.client_id
        )
        logger.info(f"Event created: {event_id} for client {client_label}")
        return event_id

    def update_event(self, event_id: str, appointment: Appointment) -> bool:
        if event_id in self._events:
            status = self._events[event_id][1]
            self._events[event_id] = (appointment, status)
            logger.info(f"Event updated: {event_id}")
            return True
        return False

    def delete_event(self, event_id: str) -> bool:
        if event_id in self._events:
            del self._events[event_id]
            logger.info(f"Event deleted: {event_id}")
            return True
        return False

    def get_event_status(self, event_id: str) -> SyncStatus | None:
        if event_id in self._events:
            # Mocking a random response from the client for demonstration
            # In a real scenario, this would be the actual guest response from the API
            return random.choice(list(SyncStatus))
        return None
