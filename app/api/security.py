"""Autenticação administrativa para integrações confiáveis com o backend."""
import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


admin_bearer = HTTPBearer(auto_error=False, scheme_name="AdminToken")


def require_admin(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(admin_bearer)
    ],
) -> None:
    expected = os.getenv("ADMIN_API_TOKEN", "").strip()
    if not expected:
        raise HTTPException(503, "Acesso administrativo não configurado")
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(
            401,
            "Credenciais administrativas inválidas ou ausentes",
            headers={"WWW-Authenticate": "Bearer"},
        )
