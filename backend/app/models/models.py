import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    FOLLOW_UP = "follow_up"
    QUALIFIED = "qualified"
    ESCALATED = "escalated"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityType(str, enum.Enum):
    LEAD_CREATED = "lead_created"
    STATUS_CHANGE = "status_change"
    CALL = "call"
    EMAIL = "email"
    NOTE = "note"
    FOLLOW_UP_SCHEDULED = "follow_up_scheduled"
    ESCALATED = "escalated"
    ASSIGNED = "assigned"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    leads = relationship("Lead", back_populates="agent")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    source = Column(String, nullable=False, default="unknown")  # e.g. website, portal, referral
    property_interest = Column(String, nullable=True)
    status = Column(Enum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    agent_id = Column(String, ForeignKey("agents.id"), nullable=True)
    notes = Column(Text, nullable=True)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    agent = relationship("Agent", back_populates="leads")
    activities = relationship(
        "Activity", back_populates="lead", cascade="all, delete-orphan",
        order_by="Activity.created_at.desc()",
    )


class Activity(Base):
    __tablename__ = "activities"

    id = Column(String, primary_key=True, default=gen_uuid)
    lead_id = Column(String, ForeignKey("leads.id"), nullable=False)
    type = Column(Enum(ActivityType), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead", back_populates="activities")
