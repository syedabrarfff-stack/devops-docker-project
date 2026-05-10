"""
Team member identity registry — human personas for Aliyar Solutions.
All client-facing communication originates from these identities.
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    name = Column(String(120), nullable=False)
    first_name = Column(String(60), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    phone = Column(String(40), default="")
    linkedin = Column(String(200), default="")

    # Organisational position
    department = Column(String(120), nullable=False)
    role = Column(String(120), nullable=False)
    seniority = Column(String(60), default="Senior")   # Junior | Mid | Senior | Lead | Head

    # Routing keys — which service_category codes this member covers
    service_categories = Column(JSON, default=list)     # e.g. ["devops", "cloud", "cicd"]
    specializations = Column(JSON, default=list)        # free-text skills

    # Communication personality
    communication_style = Column(String(60), default="professional")  # warm | direct | consultative | technical
    personality_traits = Column(JSON, default=list)     # ["analytical", "empathetic", ...]
    tone_keywords = Column(JSON, default=list)          # words that characterise their writing

    # Email / message signature block (plain text, used in outreach)
    email_signature = Column(Text, default="")

    # Proposal authorship
    proposal_title = Column(String(200), default="")    # "Solutions Architect — Cloud & DevOps"

    # Flags
    is_active = Column(Boolean, default=True)
    is_client_facing = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
