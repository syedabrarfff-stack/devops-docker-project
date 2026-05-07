from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ApprovalCreate(BaseModel):
    title: str
    action_type: str
    summary: str
    risk_level: str = "medium"
    estimated_cost: Optional[str] = None
    benefits: Optional[str] = None
    risks: Optional[str] = None
    rollback_plan: Optional[str] = None
    payload: dict = {}


class ApprovalDecision(BaseModel):
    status: str          # "approved" | "rejected"
    captain_note: Optional[str] = None


class ApprovalOut(BaseModel):
    id: int
    title: str
    action_type: str
    summary: str
    risk_level: str
    estimated_cost: Optional[str]
    benefits: Optional[str]
    risks: Optional[str]
    rollback_plan: Optional[str]
    status: str
    captain_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
