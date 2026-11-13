import re
import os
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.client_endpoints import get_client_service
from app.api.client_endpoints import router as client_router
from app.api.endpoints import (
    get_appointment_service,
    get_service_service,
    router,
    service_keepalive_router,
)
from app.api.registration_endpoints import get_registration_service
from app.api.registration_endpoints import router as registration_router
from app.domain.models import DuplicateClientError
from app.infrastructure.calendar.google_mock import GoogleMockCalendar
from app.infrastructure.database.base import (
    AppointmentDatabaseError,
    ClientDatabaseError,
    RegistrationDatabaseError,
    ServiceDatabaseError,
)
from app.infrastructure.database.config import load_supabase_config
from app.infrastructure.database.memory import InMemoryClientDatabase, InMemoryDatabase
from app.infrastructure.database.registration_repository import (
    InMemoryRegistrationRepository,
    SupabaseRegistrationRepository,
)
from app.services.appointment_service import AppointmentService
from app.services.client_service import ClientService
from app.services.registration_service import RegistrationService
from app.services.service_service import ServiceService


def get_version_from_changelog():
    try:
        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r"\[(\d+\.\d+\.\d+)\]", content)
            if match:
                return match.group(1)
    except Exception as e:
        from app.core.logging_config import logger

        logger.warning(f"Could not read version from CHANGELOG.md: {e}")
    return "0.0.0"


app = FastAPI(
    title="NailFlows API",
    description="""
    API para cadastro de clientes e automação de agendamentos de Nail Designers.
    Permite a gestão de clientes e compromissos, integração com calendário e sincronização de status de confirmação.
    """,
    version=get_version_from_changelog(),
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup infrastructure
from app.core.logging_config import logger
from app.infrastructure.database.supabase import (
    SupabaseClientDatabase,
    SupabaseDatabase,
    SupabaseServiceDatabase,
)

supabase_url, supabase_key = load_supabase_config()

if supabase_url and supabase_key:
    logger.info("Using real Supabase Database connection")
    db = SupabaseDatabase(supabase_url, supabase_key)
    client_db = SupabaseClientDatabase(supabase_url, supabase_key)
    service_db = SupabaseServiceDatabase(supabase_url, supabase_key)
    registration_repository = SupabaseRegistrationRepository(supabase_url, supabase_key)
else:
    logger.warning("Supabase não configurado. Usando banco de dados em memória.")
    db = InMemoryDatabase()
    client_db = InMemoryClientDatabase()
    service_db = None
    registration_repository = InMemoryRegistrationRepository()

# As bibliotecas Google só são importadas quando a integração é habilitada.
backend = os.getenv("CALENDAR_BACKEND", "mock").strip().lower()
if backend == "google":
    from app.infrastructure.calendar.google import GoogleCalendar, CalendarError
    from app.api.google_endpoints import router as google_router

    calendar = GoogleCalendar()
    app.state.google_calendar = calendar
    app.include_router(google_router)

    @app.exception_handler(CalendarError)
    def handle_calendar_error(request: Request, exc: CalendarError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})
elif backend == "mock":
    calendar = GoogleMockCalendar()
else:
    raise ValueError("CALENDAR_BACKEND deve ser mock ou google")

appointment_service = AppointmentService(db, calendar, service_db)
client_service = ClientService(client_db)
service_service = ServiceService(service_db) if service_db else None
registration_service = RegistrationService(
    registration_repository,
    client_service,
    frontend_url=os.getenv("FRONTEND_URL", "http://localhost:3000").strip(),
)

# Inject the service into FastAPI dependencies
app.dependency_overrides[get_appointment_service] = lambda: appointment_service
app.dependency_overrides[get_client_service] = lambda: client_service
app.dependency_overrides[get_service_service] = lambda: service_service
app.dependency_overrides[get_registration_service] = lambda: registration_service

app.include_router(service_keepalive_router)
app.include_router(router)
app.include_router(client_router)
app.include_router(registration_router)


@app.exception_handler(DuplicateClientError)
def handle_duplicate_client(request: Request, exc: DuplicateClientError):
    return JSONResponse(status_code=409, content={"detail": str(exc), "field": exc.field})


@app.exception_handler(ClientDatabaseError)
def handle_client_database_error(request: Request, exc: ClientDatabaseError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Não foi possível acessar o cadastro de clientes. Tente novamente."
        },
    )


@app.exception_handler(RegistrationDatabaseError)
def handle_registration_database_error(request: Request, exc: RegistrationDatabaseError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Não foi possível acessar os convites. Tente novamente."},
    )


@app.exception_handler(AppointmentDatabaseError)
def handle_appointment_database_error(request: Request, exc: AppointmentDatabaseError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Não foi possível acessar os agendamentos. Tente novamente."
        },
    )


@app.exception_handler(ServiceDatabaseError)
def handle_service_database_error(request: Request, exc: ServiceDatabaseError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Não foi possível acessar os serviços. Tente novamente."},
    )


@app.get("/")
def root():
    return {"message": "Welcome to NailFlows API - Nail Designer Automation"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)
