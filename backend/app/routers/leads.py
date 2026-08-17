from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import Lead, Activity, ActivityType, LeadStatus
from app.schemas.schemas import LeadOut, LeadDetailOut, LeadCreate, LeadUpdate, ActivityCreate, ActivityOut

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=list[LeadOut])
def list_leads(
    status: Optional[LeadStatus] = None,
    agent_id: Optional[str] = None,
    stale_hours: Optional[int] = Query(
        default=None,
        description="Only return leads with no activity in the last N hours (used by n8n escalation check)",
    ),
    db: Session = Depends(get_db),
):
    query = select(Lead)
    if status:
        query = query.where(Lead.status == status)
    if agent_id:
        query = query.where(Lead.agent_id == agent_id)

    leads = db.execute(query.order_by(Lead.created_at.desc())).scalars().all()

    if stale_hours is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - stale_hours * 3600
        leads = [
            l for l in leads
            if (l.last_contacted_at is None and l.created_at.timestamp() < cutoff)
            or (l.last_contacted_at is not None and l.last_contacted_at.timestamp() < cutoff)
        ]

    return leads


@router.get("/{lead_id}", response_model=LeadDetailOut)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("", response_model=LeadOut, status_code=201)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**payload.model_dump())
    db.add(lead)
    db.flush()
    db.add(Activity(
        lead_id=lead.id,
        type=ActivityType.LEAD_CREATED,
        description=f"Lead manually created from source: {payload.source}",
    ))
    db.commit()
    db.refresh(lead)
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: str, payload: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    updates = payload.model_dump(exclude_unset=True)
    old_status = lead.status
    old_agent = lead.agent_id

    for field, value in updates.items():
        setattr(lead, field, value)

    # Auto-log meaningful changes as activities so the dashboard timeline
    # stays accurate without every caller needing to remember to log it.
    if "status" in updates and updates["status"] != old_status:
        db.add(Activity(
            lead_id=lead.id,
            type=ActivityType.STATUS_CHANGE,
            description=f"Status changed from {old_status.value} to {updates['status'].value}",
        ))
        if updates["status"] == LeadStatus.ESCALATED:
            db.add(Activity(
                lead_id=lead.id,
                type=ActivityType.ESCALATED,
                description="Lead escalated due to inactivity",
            ))

    if "agent_id" in updates and updates["agent_id"] != old_agent:
        db.add(Activity(
            lead_id=lead.id,
            type=ActivityType.ASSIGNED,
            description=f"Lead assigned to agent {updates['agent_id']}",
        ))

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()


@router.post("/{lead_id}/activities", response_model=ActivityOut, status_code=201)
def add_activity(lead_id: str, payload: ActivityCreate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    activity = Activity(lead_id=lead_id, **payload.model_dump())
    db.add(activity)

    # Logging a call/email counts as contact for staleness tracking
    if payload.type in (ActivityType.CALL, ActivityType.EMAIL):
        lead.last_contacted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(activity)
    return activity


@router.get("/{lead_id}/activities", response_model=list[ActivityOut])
def list_activities(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead.activities
