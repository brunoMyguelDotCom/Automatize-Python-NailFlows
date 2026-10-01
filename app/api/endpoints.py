from fastapi import APIRouter, Depends, HTTPException
from typing import List, Annotated
from app.domain.models import Appointment
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])

# Dependency to get the service (will be injected by main.py)
def get_appointment_service() -> AppointmentService:
    # This function will be overridden in main.py using app.dependency_overrides
    # To avoid type errors during startup, we return a dummy or handle it via the override
    raise NotImplementedError("This dependency is provided by main.py")

# Use Annotated for cleaner dependency injection
# Note: We use a lambda or a simple function for the dependency, but the type here
# is just for the editor/IDE. FastAPI uses the 'Depends()' for the actual injection.
AppointmentServiceDep = Annotated[AppointmentService, Depends(get_appointment_service)]

@router.post("/", response_model=Appointment, status_code=201)
def create_appointment(appointment: Appointment, service: AppointmentServiceDep):
    return service.create_appointment(appointment)

@router.get("/", response_model=List[Appointment])
def list_appointments(service: AppointmentServiceDep):
    return service.list_appointments()

@router.get("/{id}", response_model=Appointment)
def get_appointment(id: str, service: AppointmentServiceDep):
    appointment = service.get_appointment(id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.patch("/{id}", response_model=Appointment)
def update_appointment(id: str, appointment: Appointment, service: AppointmentServiceDep):
    try:
        return service.update_appointment(id, appointment)
    except HTTPException as e:
        raise e

@router.delete("/{id}")
def delete_appointment(id: str, service: AppointmentServiceDep):
    success = service.cancel_appointment(id)
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"detail": "Appointment cancelled successfully"}

@router.post("/{id}/sincronizar", response_model=Appointment)
def sync_appointment(id: str, service: AppointmentServiceDep):
    return service.synchronize_status(id)
