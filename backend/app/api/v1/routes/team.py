"""
JARVIS Team Registry API — human identity system for Aliyar Solutions.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.v1.routes.auth import get_current_captain
from app.core.rate_limit import limiter
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/team", tags=["team"], dependencies=[Depends(get_current_captain)])


# ── Pydantic models ───────────────────────────────────────────────────────────

class TeamMemberUpdate(BaseModel):
    role: Optional[str] = Field(default=None, max_length=200)
    department: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    linkedin: Optional[str] = Field(default=None, max_length=500)
    service_categories: Optional[List[str]] = None
    specializations: Optional[List[str]] = None
    communication_style: Optional[str] = Field(default=None, max_length=500)
    personality_traits: Optional[List[str]] = None
    tone_keywords: Optional[List[str]] = None
    email_signature: Optional[str] = Field(default=None, max_length=5_000)
    proposal_title: Optional[str] = Field(default=None, max_length=300)
    is_active: Optional[bool] = None
    is_client_facing: Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/members")
async def list_members(
    active_only: bool = True,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    from app.services.team.team_service import get_all_members
    members = await get_all_members(db, active_only=active_only)
    if department:
        members = [m for m in members if department.lower() in m.department.lower()]
    return {
        "members": [_serialize(m) for m in members],
        "count": len(members),
    }


@router.get("/members/{member_id}")
async def get_member(member_id: int, db: AsyncSession = Depends(get_db)):
    from app.services.team.team_service import get_member_by_id
    member = await get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    return _serialize(member)


@router.get("/members/for-service/{service_category}")
async def get_member_for_service(service_category: str, db: AsyncSession = Depends(get_db)):
    """Return the best-fit team member for a given service category."""
    from app.services.team.team_service import get_member_for_service
    member = await get_member_for_service(db, service_category)
    if not member:
        raise HTTPException(status_code=404, detail="No team member found for this service category")
    return _serialize(member)


@router.patch("/members/{member_id}")
@limiter.limit("20/minute")
async def update_member(request: Request, member_id: int, data: TeamMemberUpdate, db: AsyncSession = Depends(get_db)):
    from app.services.team.team_service import get_member_by_id
    member = await get_member_by_id(db, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(member, field, value)
    await db.flush()
    await db.refresh(member)
    return _serialize(member)


@router.post("/seed")
@limiter.limit("3/minute")
async def seed_team(request: Request, db: AsyncSession = Depends(get_db)):
    """Seed the team registry with all 9 Aliyar Solutions team members."""
    from app.services.team.team_service import seed_team
    result = await seed_team(db)
    return {"status": "ok", **result}


@router.get("/stats")
async def team_stats(db: AsyncSession = Depends(get_db)):
    from app.services.team.team_service import get_team_stats
    return await get_team_stats(db)


@router.get("/communication-guide")
async def communication_guide():
    """Return the Aliyar Solutions communication philosophy for reference."""
    return {
        "philosophy": "Human, relaxed, emotionally aware — startup energy meets premium consulting",
        "principles": [
            "Lead with genuine curiosity, not scripted pitches",
            "Acknowledge time value — be concise, earn the next reply",
            "Use specificity over generics — mention their company, their context",
            "Never oversell — let capability speak through confidence",
            "Follow up as a colleague, not a vendor",
            "Match energy — mirror the prospect's formality level",
        ],
        "forbidden_phrases": [
            "I hope this email finds you well",
            "I wanted to reach out",
            "Synergies",
            "Best-in-class",
            "Leverage our solutions",
            "Circle back",
            "Touch base",
        ],
        "identity_policy": {
            "external_name": "Aliyar Solutions Team",
            "never_mention": ["AI", "bot", "GPT", "Claude", "autonomous", "machine-generated"],
            "always_present_as": "Premium international technology company with specialist human teams",
        },
        "agency_partnership": {
            "positioning": [
                "White-label fulfilment partner for agencies needing delivery capacity",
                "Overflow engineering team for agencies at capacity",
                "Project rescue specialist for at-risk engagements",
            ],
            "approach": "Trust-first, no hard sell — prove capability before discussing volume",
        },
    }


# ── Serialiser ────────────────────────────────────────────────────────────────

def _serialize(m) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "first_name": m.first_name,
        "email": m.email,
        "phone": m.phone,
        "linkedin": m.linkedin,
        "department": m.department,
        "role": m.role,
        "seniority": m.seniority,
        "service_categories": m.service_categories or [],
        "specializations": m.specializations or [],
        "communication_style": m.communication_style,
        "personality_traits": m.personality_traits or [],
        "tone_keywords": m.tone_keywords or [],
        "email_signature": m.email_signature,
        "proposal_title": m.proposal_title,
        "is_active": m.is_active,
        "is_client_facing": m.is_client_facing,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
