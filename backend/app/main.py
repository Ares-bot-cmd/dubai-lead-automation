from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import Base, engine
from app.routers import webhook, leads, agents

# Creates tables if they don't exist. Fine for SQLite/demo purposes;
# swap for Alembic migrations if this grows into a real production app.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dubai Real Estate Lead Automation API",
    description="Backend for lead intake, management, and activity tracking. "
                 "n8n workflows call /webhook/lead to create leads and the "
                 "/leads endpoints to read/update state for follow-up and escalation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your dashboard's domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(leads.router)
app.include_router(agents.router)


@app.get("/health")
def health():
    return {"status": "ok"}
