from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import re
from app.api.endpoints import get_appointment_service, router
from app.api.client_endpoints import get_client_service, router as client_router
from app.services.appointment_service import AppointmentService
from app.services.client_service import ClientService
from app.infrastructure.database.base import ClientDatabaseError
from app.infrastructure.database.memory import InMemoryClientDatabase, InMemoryDatabase
from app.infrastructure.calendar.google_mock import GoogleMockCalendar

def get_version_from_changelog():
    try:
        with open("CHANGELOG.md", "r", encoding="utf-8") as f:
            content = f.read()
            # Look for the first occurrence of [x.x.x]
            match = re.search(r"\[(\d+\.\d+\.\d+)\]", content)
            if match:
                return match.group(1)
    except Exception as e:
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

# Setup infrastructure
from app.core.logging_config import logger
from app.infrastructure.database.supabase import SupabaseClientDatabase, SupabaseDatabase

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    logger.info("Using real Supabase Database connection")
    db = SupabaseDatabase()
    client_db = SupabaseClientDatabase(supabase_url, supabase_key)
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY not found. Falling back to IN-MEMORY MOCK database.")
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
        content={"detail": "Não foi possível acessar o cadastro de clientes. Tente novamente."},
    )

@app.get("/")
def root():
    return {"message": "Welcome to NailFlows API - Nail Designer Automation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
