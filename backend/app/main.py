import os
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database_init import init_db
from app.routers import (
    dashboard, agent, jobs, profile, resumes, contacts,
    applications, integrations, policy, audit, worker, voice,
    auth, admin
)

_worker_stop_event = threading.Event()
_worker_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_thread, _worker_stop_event
    # Initialize database tables and seed defaults
    init_db()
    os.makedirs("./data/resumes", exist_ok=True)
    os.makedirs("./data/uploads", exist_ok=True)

    # Automatically run autonomous worker inside the web service when enabled (100% Free on Render/Cloud)
    if os.environ.get("RUN_WORKER_IN_APP", "false").lower() in ("true", "1", "yes"):
        try:
            from worker import worker_loop
            _worker_stop_event.clear()
            _worker_thread = threading.Thread(
                target=worker_loop,
                args=(_worker_stop_event,),
                name="CareerPilot-Embedded-Worker",
                daemon=True
            )
            _worker_thread.start()
            print("[CareerPilot API] Autonomous background worker started inside web service.", flush=True)
        except Exception as e:
            print(f"[CareerPilot API] Warning: Failed to launch embedded worker: {e}", flush=True)

    yield

    if _worker_thread and _worker_thread.is_alive():
        print("[CareerPilot API] Gracefully stopping embedded background worker...", flush=True)
        _worker_stop_event.set()
        _worker_thread.join(timeout=3)

app = FastAPI(
    title="CareerPilot AI API",
    description="Autonomous Job Discovery, Resume Intelligence, Application Automation and HR Outreach Platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development allow all for easy local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(dashboard.router)
app.include_router(agent.router)
app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(resumes.router)
app.include_router(contacts.router)
app.include_router(applications.router)
app.include_router(integrations.router)
app.include_router(policy.router)
app.include_router(audit.router)
app.include_router(worker.router)
app.include_router(voice.router)
app.include_router(auth.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {
        "name": "CareerPilot AI API",
        "version": "2.0.0",
        "status": "ONLINE",
        "documentation": "/docs",
        "message": "CareerPilot AI backend is active. Access frontend via Vite on http://localhost:5173"
    }

@app.get("/health")
def health():
    return {"status": "HEALTHY"}

@app.get("/profile_photo.jpg")
def get_profile_photo():
    photo_path = "./data/profile_photo.jpg"
    if os.path.exists(photo_path):
        return FileResponse(photo_path, media_type="image/jpeg")
    return {"error": "Photo not found"}

@app.get("/SK_Adil_Raja_Resume.pdf")
def get_original_resume_pdf():
    pdf_path = "./data/resumes/SK_Adil_Raja_Resume.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename="SK_Adil_Raja_Resume.pdf")
    return {"error": "Resume PDF not found"}
