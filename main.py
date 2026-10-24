import re
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.client_endpoints import get_client_service
from app.api.client_endpoints import router as client_router
from app.api.endpoints import get_appointment_service, router
from app.infrastructure.calendar.google_mock import GoogleMockCalendar
from app.infrastructure.database.base import ClientDatabaseError, AppointmentDatabaseError
from app.infrastructure.database.config import load_supabase_config
from app.infrastructure.database.memory import InMemoryClientDatabase, InMemoryDatabase
from app.services.appointment_service import AppointmentService
from app.services.client_service import ClientService


def get_version_from_changelog():
    try:
        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            content = f.read()
            # Look for the first occurrence of [x.x.x]
            match = re.search(r"\[(\d+\.\d+\.\d+)\]", content)
            if match:
                return match.group(1)
    except Exception as e:  # noqa: BLE001
        # Import logger here to avoid circular imports or ensure it's available
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
)

supabase_url, supabase_key = load_supabase_config()

if supabase_url and supabase_key:
    logger.info("Using real Supabase Database connection")
    db = SupabaseDatabase(supabase_url, supabase_key)
    client_db = SupabaseClientDatabase(supabase_url, supabase_key)
else:
    logger.warning(
        "Supabase não configurado. Usando banco de dados em memória."
    )
    db = InMemoryDatabase()
    client_db = InMemoryClientDatabase()

calendar = GoogleMockCalendar()
appointment_service = AppointmentService(db, calendar)
client_service = ClientService(client_db)

# Inject the service into FastAPI dependencies
app.dependency_overrides[get_appointment_service] = lambda: appointment_service
app.dependency_overrides[get_client_service] = lambda: client_service

app.include_router(router)
app.include_router(client_router)


@app.exception_handler(ClientDatabaseError)
def handle_client_database_error(request: Request, exc: ClientDatabaseError):
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Não foi possível acessar o cadastro de clientes. Tente novamente."
        },
    )


@app.exception_handler(AppointmentDatabaseError)
def handle_appointment_database_error(request: Request, exc: AppointmentDatabaseError):
    return JSONResponse(
        status_code=503,
        content={"detail": "Não foi possível acessar os agendamentos. Tente novamente."},
    )


@app.get("/")
def root():
    return {"message": "Welcome to NailFlows API - Nail Designer Automation"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
