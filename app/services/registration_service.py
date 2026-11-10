
import hashlib
import secrets

from datetime import datetime, timedelta, timezone
from app.domain.models import RegistrationLinkError

from app.infrastructure.database.registration_repository import (
    RegistrationLink,
)


class RegistrationService:
    def __init__(
        self,
        repository,
        client_service,
        frontend_url: str,
    ):
        self.repository = repository
        self.client_service = client_service
        self.frontend_url = frontend_url.rstrip("/")

    def _hash_token(self, token: str):
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    def create_link(self):
        token = secrets.token_urlsafe(32)

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(hours=6)
        )

        link = RegistrationLink(
            token_hash=self._hash_token(token),
            expires_at=expires_at,
        )

        self.repository.save(link)

        return {
            "url": (
                f"{self.frontend_url}"
                f"/cadastro/{token}"
            ),
            "expires_at": expires_at.isoformat(),
        }

    def validate_link(self, token: str):
        link = self.repository.find_by_hash(
            self._hash_token(token)
        )

        now = datetime.now(timezone.utc)

        if link is None:
            raise RegistrationLinkError("Link inválido")

        if link.used_at is not None:
            raise RegistrationLinkError("Link já utilizado")

        if now >= link.expires_at:
            raise RegistrationLinkError("Link expirado")

        return {"valid": True}

    def register_client(self, token, data):
        token_hash = self._hash_token(token)
        return self.repository.register_client(
            token_hash, data, self.client_service,
        )
