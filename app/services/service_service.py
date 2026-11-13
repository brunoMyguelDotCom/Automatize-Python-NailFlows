from fastapi import HTTPException

from app.core.logging_config import logger
from app.domain.models import Service, ServiceCreate, ServiceUpdate
from app.infrastructure.database.base import (
    BaseServiceDatabase,
)


class ServiceService:
    def __init__(self, db: BaseServiceDatabase):
        self.db = db

    def create_service(self, service_data: ServiceCreate) -> Service:
        service = Service(**service_data.model_dump())
        return self.db.create(service)

    def list_services(self, active_only: bool = False) -> list[Service]:
        services = self.db.list_all()
        if active_only:
            services = [s for s in services if s.active]
        return services

    def get_service(self, service_id: str) -> Service:
        service = self.db.get_by_id(service_id)
        if service is None:
            raise HTTPException(status_code=404, detail="Serviço não encontrado")
        return service

    def update_service(self, service_id: str, service_data: ServiceUpdate) -> Service:
        existing = self.get_service(service_id)
        changes = service_data.model_dump(exclude_unset=True)

        updated_service = Service(**{**existing.model_dump(), **changes})
        saved_service = self.db.update(service_id, updated_service)
        if saved_service is None:
            raise HTTPException(status_code=404, detail="Serviço não encontrado")
        return saved_service

    def delete_service(self, service_id: str) -> bool:
        """
        Implementa a deleção lógica (soft delete).
        Em vez de remover do banco, define o serviço como inativo.
        """
        # A ausência do serviço é um resultado esperado da API (404), não uma
        # falha de acesso ao banco. Mantemos a busca fora do bloco amplo para
        # não transformar HTTPException em 503.
        service = self.get_service(service_id)
        try:
            # Atualiza apenas o campo 'active' para False
            updated_service = Service(**{**service.model_dump(), "active": False})
            saved = self.db.update(service_id, updated_service)
            return saved is not None
        except Exception as e:
            logger.error("Erro inesperado ao inativar serviço: %s", str(e))
            raise HTTPException(
                status_code=503, detail="Falha ao acessar o banco de dados"
            )
