from typing import List

from fastapi import HTTPException

from app.domain.models import ClientCreate, ClientRecord, ClientUpdate
from app.infrastructure.database.base import BaseClientDatabase


class ClientService:
    def __init__(self, db: BaseClientDatabase):
        self.db = db

    def create_client(self, client_data: ClientCreate) -> ClientRecord:
        client = ClientRecord(**client_data.model_dump())
        return self.db.create(client)

    def list_clients(self) -> List[ClientRecord]:
        return self.db.list_all()

    def get_client(self, client_id: str) -> ClientRecord:
        client = self.db.get_by_id(client_id)
        if client is None:
            raise HTTPException(status_code=404, detail="Cliente não encontrada")
        return client

    def update_client(self, client_id: str, client_data: ClientUpdate) -> ClientRecord:
        existing = self.get_client(client_id)
        changes = client_data.model_dump(exclude_unset=True)
        updated_client = ClientRecord.model_validate({**existing.model_dump(), **changes})
        saved_client = self.db.update(client_id, updated_client)
        if saved_client is None:
            raise HTTPException(status_code=404, detail="Cliente não encontrada")
        return saved_client

    def delete_client(self, client_id: str) -> bool:
        return self.db.delete(client_id)
