from fastapi import HTTPException

from app.core.logging_config import logger
from app.domain.models import ClientCreate, ClientRecord, ClientUpdate
from app.infrastructure.database.base import (
    BaseClientDatabase,
    ForeignKeyViolationError,
)


class ClientService:
    def __init__(self, db: BaseClientDatabase):
        self.db = db

    def create_client(self, client_data: ClientCreate) -> ClientRecord:
        client = ClientRecord(**client_data.model_dump())
        return self.db.create(client)

    def list_clients(self) -> list[ClientRecord]:
        return self.db.list_all()

    def get_client(self, client_id: str) -> ClientRecord:
        client = self.db.get_by_id(client_id)
        if client is None:
            raise HTTPException(status_code=404, detail="Cliente não encontrada")
        return client

    def update_client(self, client_id: str, client_data: ClientUpdate) -> ClientRecord:
        existing = self.get_client(client_id)
        changes = client_data.model_dump(exclude_unset=True)
        updated_client = ClientRecord.model_validate(
            {**existing.model_dump(), **changes}
        )
        saved_client = self.db.update(client_id, updated_client)
        if saved_client is None:
            raise HTTPException(status_code=404, detail="Cliente não encontrada")
        return saved_client

    def delete_client(self, client_id: str) -> bool:
        try:
            return self.db.delete(client_id)
        except ForeignKeyViolationError:
            raise HTTPException(
                status_code=400,
                detail="Não é possível deletar a cliente pois ela possui agendamentos vinculados",
            )
        except Exception as e:
            logger.error("Erro inesperado ao deletar cliente: %s", str(e))
            raise HTTPException(
                status_code=503, detail="Falha ao acessar o banco de dados"
            )
