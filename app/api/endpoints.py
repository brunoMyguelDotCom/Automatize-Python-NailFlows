from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import (
    Appointment,
    AppointmentCreate,
    Service,
    ServiceCreate,
    ServiceUpdate,
)
from app.services.appointment_service import AppointmentService
from app.services.service_service import ServiceService

router = APIRouter()

# --- Agendamentos ---
appointment_router = APIRouter(prefix="/agendamentos", tags=["agendamentos"])


def get_appointment_service() -> AppointmentService:
    raise NotImplementedError("This dependency is provided by main.py")


AppointmentServiceDep = Annotated[AppointmentService, Depends(get_appointment_service)]


@appointment_router.post(
    "/",
    response_model=Appointment,
    status_code=201,
    summary="Criar novo agendamento",
    description="Cria um novo agendamento no sistema. O agendamento depende de um client_id e service_id válidos e a data deve ser futura.",
)
def create_appointment(appointment: AppointmentCreate, service: AppointmentServiceDep):
    return service.create_appointment(appointment)


@appointment_router.get(
    "/",
    response_model=list[Appointment],
    summary="Listar todos os agendamentos",
    description="Retorna uma lista de todos os agendamentos registrados.",
)
def list_appointments(
    service: AppointmentServiceDep,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    active_only: bool = False,
):
    return service.list_appointments(
        start_date=start_date, end_date=end_date, active_only=active_only
    )


@appointment_router.get(
    "/{id}",
    response_model=Appointment,
    summary="Obter agendamento por ID",
    description="Retorna os detalhes de um agendamento específico baseado no seu ID.",
)
def get_appointment(id: str, service: AppointmentServiceDep):
    appointment = service.get_appointment(id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return appointment


@appointment_router.patch(
    "/{id}",
    response_model=Appointment,
    summary="Atualizar agendamento",
    description="Atualiza parcialmente os dados de um agendamento existente.",
)
def update_appointment(
    id: str, appointment: AppointmentCreate, service: AppointmentServiceDep
):
    try:
        return service.update_appointment(id, appointment)
    except HTTPException:
        raise


@appointment_router.delete(
    "/{id}",
    summary="Cancelar agendamento",
    description="Remove um agendamento do sistema e cancela a reserva.",
)
def delete_appointment(id: str, service: AppointmentServiceDep):
    success = service.cancel_appointment(id)
    if not success:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return {"detail": "Agendamento cancelado com sucesso"}


@appointment_router.post(
    "/{id}/sincronizar",
    response_model=Appointment,
    summary="Sincronizar com Google Calendar",
    description="Força a sincronização do status do agendamento com o Google Calendar.",
)
def sync_appointment(id: str, service: AppointmentServiceDep):
    return service.synchronize_status(id)


# --- Serviços ---
service_router = APIRouter(prefix="/servicos", tags=["serviços"])


def get_service_service() -> ServiceService:
    raise NotImplementedError("This dependency is provided by main.py")


ServiceServiceDep = Annotated[ServiceService, Depends(get_service_service)]


@service_router.post(
    "/",
    response_model=Service,
    status_code=201,
    summary="Criar novo serviço",
    description="Cadastra um novo serviço no sistema.",
)
def create_service(service_data: ServiceCreate, service: ServiceServiceDep):
    return service.create_service(service_data)


@service_router.get(
    "/",
    response_model=list[Service],
    summary="Listar todos os serviços",
    description="Retorna uma lista de todos os serviços cadastrados.",
)
def list_services(service: ServiceServiceDep, active_only: bool = False):
    return service.list_services(active_only=active_only)


@service_router.get(
    "/{id}",
    response_model=Service,
    summary="Obter serviço por ID",
    description="Retorna os detalhes de um serviço específico.",
)
def get_service(id: str, service: ServiceServiceDep):
    return service.get_service(id)


@service_router.patch(
    "/{id}",
    response_model=Service,
    summary="Atualizar serviço",
    description="Atualiza parcialmente os dados de um serviço existente.",
)
def update_service(id: str, service_data: ServiceUpdate, service: ServiceServiceDep):
    return service.update_service(id, service_data)


@service_router.delete(
    "/{id}",
    summary="Deletar serviço",
    description="Remove um serviço do sistema. Bloqueado se houver agendamentos vinculados.",
)
def delete_service(id: str, service: ServiceServiceDep):
    success = service.delete_service(id)
    if not success:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    return {"detail": "Serviço inativado com sucesso"}


router.include_router(appointment_router)
router.include_router(service_router)
