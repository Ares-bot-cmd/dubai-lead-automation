from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Lead, Activity, ActivityType
from app.schemas.schemas import LeadWebhookIn, LeadOut
import os

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Simple shared-secret check so random internet traffic can't create leads.
# Set WEBHOOK_SECRET in your environment and send it as X-Webhook-Secret.
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")


def verify_secret(x_webhook_secret: str = Header(default="")):
    if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


@router.post("/lead", response_model=LeadOut, status_code=201, dependencies=[Depends(verify_secret)])
def receive_lead(payload: LeadWebhookIn, db: Session = Depends(get_db)):
    """
    Entry point for new leads from external sources (property portal,
    website contact form, n8n, etc). Creates the lead and logs the
    initial activity. n8n should call this endpoint, then continue its
    own workflow (agent assignment notification, follow-up scheduling)
    against the returned lead id.
    """
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="Lead name is required")

    lead = Lead(
        name=payload.name.strip(),
        email=payload.email,
        phone=payload.phone,
        source=payload.source,
        property_interest=payload.property_interest,
        notes=payload.notes,
    )
    db.add(lead)
    db.flush()  # get lead.id before commit

    activity = Activity(
        lead_id=lead.id,
        type=ActivityType.LEAD_CREATED,
        description=f"Lead captured from source: {payload.source}",
    )
    db.add(activity)
    db.commit()
    db.refresh(lead)
    return lead
