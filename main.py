from fastapi import FastAPI
import os
import re
from app.api.endpoints import get_appointment_service, router
from app.services.appointment_service import AppointmentService
from app.infrastructure.database.memory import InMemoryDatabase
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
    API para automação de agendamentos de Nail Designers.
    Permite a gestão de compromissos, integração com calendário e sincronização de status de confirmação.
    """,
    version=get_version_from_changelog(),
)

# Setup infrastructure
from app.core.logging_config import logger
from app.infrastructure.database.supabase import SupabaseDatabase

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    logger.info("Using real Supabase Database connection")
    db = SupabaseDatabase()
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY not found. Falling back to IN-MEMORY MOCK database.")
    db = InMemoryDatabase()

calendar = GoogleMockCalendar()
appointment_service = AppointmentService(db, calendar)

# Inject the service into FastAPI dependencies
app.dependency_overrides[get_appointment_service] = lambda: appointment_service

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Welcome to NailFlows API - Nail Designer Automation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
