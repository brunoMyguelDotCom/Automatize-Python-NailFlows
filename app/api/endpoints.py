from fastapi import APIRouter, Depends, HTTPException
from typing import List, Annotated
from app.domain.models import Appointment, AppointmentCreate
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])

# Dependency to get the service (will be injected by main.py)
def get_appointment_service() -> AppointmentService:
    # This function will be overridden in main.py using app.dependency_overrides
    raise NotImplementedError("This dependency is provided by main.py")

AppointmentServiceDep = Annotated[AppointmentService, Depends(get_appointment_service)]

@router.post("/", response_model=Appointment, status_code=201,
             summary="Criar novo agendamento",
             description="Cria um novo agendamento no sistema. O ID do agendamento é gerado automaticamente pelo servidor.")
def create_appointment(appointment: AppointmentCreate, service: AppointmentServiceDep):
    return service.create_appointment(appointment)

@router.get("/", response_model=List[Appointment],
             summary="Listar todos os agendamentos",
             description="Retorna uma lista de todos os agendamentos registrados.")
def list_appointments(service: AppointmentServiceDep):
    return service.list_appointments()

@router.get("/{id}", response_model=Appointment,
             summary="Obter agendamento por ID",
             description="Retorna os detalhes de um agendamento específico baseado no seu ID.")
def get_appointment(id: str, service: AppointmentServiceDep):
    appointment = service.get_appointment(id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return appointment

@router.patch("/{id}", response_model=Appointment,
             summary="Atualizar agendamento",
             description="Atualiza parcialmente os dados de um agendamento existente.")
def update_appointment(id: str, appointment: AppointmentCreate, service: AppointmentServiceDep):
    try:
        return service.update_appointment(id, appointment)
    except HTTPException as e:
        raise e

@router.delete("/{id}",
             summary="Cancelar agendamento",
             description="Remove um agendamento do sistema e cancela a reserva.")
def delete_appointment(id: str, service: AppointmentServiceDep):
    success = service.cancel_appointment(id)
    if not success:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return {"detail": "Agendamento cancelado com sucesso"}

@router.post("/{id}/sincronizar", response_model=Appointment,
             summary="Sincronizar com Google Calendar",
             description="Força a sincronização do status do agendamento com o Google Calendar.")
def sync_appointment(id: str, service: AppointmentServiceDep):
    return service.synchronize_status(id)
