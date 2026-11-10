
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from app.domain.models import RegistrationLinkError
from app.domain.models import ClientRecord
from pydantic import AwareDatetime, BaseModel, Field

from app.infrastructure.database.base import RegistrationDatabaseError, duplicate_client_error
from app.infrastructure.database.supabase import SupabaseRestDatabase


@dataclass
class RegistrationLink:
    token_hash: str
    expires_at: datetime
    used_at: datetime | None = None


class _RegistrationLinkRecord(BaseModel):
    """Valida as linhas retornadas pela API REST antes de usá-las no domínio."""

    token_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: AwareDatetime
    used_at: AwareDatetime | None = None


class SupabaseRegistrationRepository(SupabaseRestDatabase):
    """Persistência de convites e cadastro transacional via RPC PostgreSQL."""

    record_model = _RegistrationLinkRecord
    database_error = RegistrationDatabaseError

    def __init__(self, url: str, key: str):
        self.url = f"{url.rstrip('/')}/rest/v1/registration_links"
        self.rpc_url = f"{url.rstrip('/')}/rest/v1/rpc/register_client_with_invitation"
        self.key = key

    def save(self, link: RegistrationLink) -> None:
        rows = self._request(
            "POST",
            data={
                "token_hash": link.token_hash,
                "expires_at": link.expires_at.isoformat(),
                "used_at": link.used_at.isoformat() if link.used_at else None,
            },
        )
        if len(rows) != 1 or rows[0].token_hash != link.token_hash:
            raise RegistrationDatabaseError("O banco não confirmou o convite criado")

    def find_by_hash(self, token_hash: str) -> RegistrationLink | None:
        rows = self._request(
            "GET",
            params={
                "token_hash": f"eq.{token_hash}",
                "select": "token_hash,expires_at,used_at",
                "limit": "1",
            },
        )
        if not rows:
            return None
        row = rows[0]
        if row.token_hash != token_hash:
            raise RegistrationDatabaseError("O banco retornou um convite inesperado")
        return RegistrationLink(**row.model_dump())

    def register_client(self, token_hash, data, client_service=None):
        # A função SQL cria a cliente e consome o convite na mesma transação.
        # Não chama client_service: um INSERT separado quebraria essa garantia.
        headers = {
            "apikey": self.key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {self.key}"
        body = json.dumps({
            "p_token_hash": token_hash,
            "p_name": data.name,
            "p_email": str(data.email),
            "p_phone": data.phone,
        }).encode("utf-8")
        request = Request(self.rpc_url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=10) as response:
                rows = json.load(response)
            if not isinstance(rows, list) or len(rows) != 1:
                raise ValueError("Expected exactly one registered client")
            return ClientRecord.model_validate(rows[0])
        except HTTPError as exc:
            try:
                error = json.load(exc)
            except (ValueError, OSError):
                error = None
            finally:
                exc.close()
            duplicate = duplicate_client_error(error)
            if duplicate is not None:
                raise duplicate from exc
            if (
                isinstance(error, dict)
                and error.get("code") == "P0001"
                and error.get("message") in {
                    "Link inválido", "Link expirado", "Link já utilizado"
                }
            ):
                raise RegistrationLinkError(error["message"]) from exc
            raise RegistrationDatabaseError("Falha ao cadastrar cliente por convite") from exc
        except (URLError, OSError, ValueError) as exc:
            raise RegistrationDatabaseError("Falha ao cadastrar cliente por convite") from exc


class InMemoryRegistrationRepository:
    def __init__(self):
        self._links = {}
        self._lock = RLock()

    def save(self, link: RegistrationLink):
        with self._lock:
            self._links[link.token_hash] = link

    def find_by_hash(self, token_hash: str):
        with self._lock:
            return self._links.get(token_hash)

    def register_client(self, token_hash, data, client_service):
        return self.execute_if_available(
            token_hash,
            datetime.now(timezone.utc),
            lambda: client_service.create_client(data),
        )

    def execute_if_available(
        self, token_hash, now, action
    ):
        with self._lock:
            link = self._links.get(token_hash)

            if link is None:
                raise RegistrationLinkError("Link inválido")

            if link.used_at is not None:
                raise RegistrationLinkError("Link já utilizado")

            if now >= link.expires_at:
                raise RegistrationLinkError("Link expirado")

            result = action()
            link.used_at = now

            return result
