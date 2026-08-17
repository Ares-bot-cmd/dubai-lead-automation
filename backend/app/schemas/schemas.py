from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict

from app.models.models import LeadStatus, ActivityType


# ---------- Agent ----------

class AgentBase(BaseModel):
    name: str
    email: EmailStr


class AgentCreate(AgentBase):
    pass


class AgentOut(AgentBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


# ---------- Activity ----------

class ActivityCreate(BaseModel):
    type: ActivityType
    description: str


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    lead_id: str
    type: ActivityType
    description: str
    created_at: datetime


# ---------- Lead ----------

class LeadWebhookIn(BaseModel):
    """Shape expected from external lead sources (portal, form, n8n)."""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: str = "unknown"
    property_interest: Optional[str] = None
    notes: Optional[str] = None


class LeadCreate(LeadWebhookIn):
    agent_id: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[LeadStatus] = None
    agent_id: Optional[str] = None
    notes: Optional[str] = None
    last_contacted_at: Optional[datetime] = None


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    source: str
    property_interest: Optional[str]
    status: LeadStatus
    agent_id: Optional[str]
    notes: Optional[str]
    last_contacted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class LeadDetailOut(LeadOut):
    activities: list[ActivityOut] = []
