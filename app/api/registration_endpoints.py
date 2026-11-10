
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from app.domain.models import ClientRegistrationRequest
from app.domain.models import RegistrationLinkError
from app.api.security import require_admin

from app.services.registration_service import (
    RegistrationService,
)

router = APIRouter(
    prefix="/registration-links",
    tags=["Cadastro por convite"],
)


def get_registration_service():
    raise NotImplementedError(
        "Configure a dependência no main.py"
    )


@router.post("", status_code=201, dependencies=[Depends(require_admin)])
def create_link(
    service: RegistrationService = Depends(
        get_registration_service
    ),
):
    return service.create_link()


@router.get("/{token}")
def validate_link(
    token: str,
    service: RegistrationService = Depends(
        get_registration_service
    ),
):
    try:
        return service.validate_link(token)

    except RegistrationLinkError as error:
        raise HTTPException(
            status_code=410,
            detail=str(error),
        )


@router.post(
    "/{token}/register", status_code=201,
    responses={409: {"description": "E-mail ou telefone já cadastrado"}},
)
def register_client(
    token: str,
    data: ClientRegistrationRequest,
    service: RegistrationService = Depends(
        get_registration_service
    ),
):
    try:
        client = service.register_client(
            token, data
        )

        return {
            "message": "Cadastro realizado",
            "client": client,
        }

    except RegistrationLinkError as error:
        raise HTTPException(
            status_code=410,
            detail=str(error),
        )
