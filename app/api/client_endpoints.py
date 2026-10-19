from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.domain.models import ClientCreate, ClientRecord, ClientUpdate
from app.services.client_service import ClientService


router = APIRouter(prefix="/clientes", tags=["clientes"])


def get_client_service() -> ClientService:
    raise NotImplementedError("This dependency is provided by main.py")


ClientServiceDep = Annotated[ClientService, Depends(get_client_service)]


@router.post(
    "/",
    response_model=ClientRecord,
    status_code=201,
    summary="Cadastrar cliente",
    description="Cadastra uma cliente. O ID e a data de cadastro são gerados pelo servidor.",
)
def create_client(client: ClientCreate, service: ClientServiceDep):
    return service.create_client(client)


@router.get(
    "/",
    response_model=List[ClientRecord],
    summary="Listar clientes",
    description="Retorna todas as clientes cadastradas.",
)
def list_clients(service: ClientServiceDep):
    return service.list_clients()


@router.get(
    "/{id}",
    response_model=ClientRecord,
    summary="Obter cliente por ID",
    description="Retorna os dados de uma cliente cadastrada.",
)
def get_client(id: UUID, service: ClientServiceDep):
    return service.get_client(str(id))


@router.patch(
    "/{id}",
    response_model=ClientRecord,
    summary="Atualizar cliente",
    description="Atualiza somente os campos enviados. O ID e a data de cadastro são preservados.",
)
def update_client(id: UUID, client: ClientUpdate, service: ClientServiceDep):
    return service.update_client(str(id), client)


@router.delete(
    "/{id}", summary="Excluir cliente", description="Exclui uma cliente do cadastro."
)
def delete_client(id: UUID, service: ClientServiceDep):
    if not service.delete_client(str(id)):
        raise HTTPException(status_code=404, detail="Cliente não encontrada")
    return {"detail": "Cliente excluída com sucesso"}
