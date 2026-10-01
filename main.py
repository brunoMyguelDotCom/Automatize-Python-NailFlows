from fastapi import FastAPI
from app.api.endpoints import router
from app.services.appointment_service import AppointmentService
from app.infrastructure.database.memory import InMemoryDatabase
from app.infrastructure.calendar.google_mock import GoogleMockCalendar

app = FastAPI(title="NailFlows API")

# Setup infrastructure
import os
from app.core.logging_config import logger
from app.infrastructure.database.supabase import SupabaseDatabase

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if supabase_url and supabase_key:
    logger.info("Using real Supabase Database connection")
    db = SupabaseDatabase()
else:
    logger.warning("SUPABASE_URL or SUPABASE_KEY not found. Falling back to IN-MEMORY MOCK database.")
    from app.infrastructure.database.memory import InMemoryDatabase
    db = InMemoryDatabase()

calendar = GoogleMockCalendar()
appointment_service = AppointmentService(db, calendar)

# Inject the service into FastAPI dependencies
app.dependency_overrides[AppointmentService] = lambda: appointment_service

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Welcome to NailFlows API - Nail Designer Automation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
