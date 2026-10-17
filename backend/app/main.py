from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database_init import init_db
from app.routers import (
    dashboard, agent, jobs, profile, resumes, contacts,
    applications, integrations, policy, audit, worker
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed defaults
    init_db()
    os.makedirs("./data/resumes", exist_ok=True)
    os.makedirs("./data/uploads", exist_ok=True)
    yield

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
