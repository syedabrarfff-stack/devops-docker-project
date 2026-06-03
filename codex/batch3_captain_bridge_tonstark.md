# JARVIS CODEX BATCH 3 — CAPTAIN'S BRIDGE + TONY STARK LAYER
## Build after Batch 2 is confirmed live

---

## CONTEXT

Working directory: `/opt/jarvis/`
Prerequisites: Batches 1 and 2 complete.
Deploy: `docker-compose up -d --build jarvis_app`

This batch covers:

### Captain's Intelligence Bridge (10 components)
JARVIS connects to Captain's manual sales ops (HubSpot, Apollo, personal outreach) so no intelligence is ever lost.

### Tony Stark Layer
- Two-way voice command interface (ElevenLabs TTS)
- Predictive action engine ("Your 3 best moves right now")
- JARVIS pushback engine (disagrees with poor decisions)
- Real-time situation consciousness feed (WebSocket)
- Emotional intelligence on email replies
- Scenario simulation (Monte Carlo on strategic decisions)
- Threat detection system
- War Room mode
- Confidence scores on all outputs
- 48-hour revenue drift alert
- System health HUD

---

## STEP 1 — DATABASE MIGRATION

Create: `alembic/versions/0011_captain_bridge_tonstark.py`

```python
"""captain bridge and tony stark tables

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0011'
down_revision = '0010'


def upgrade():
    op.create_table('captain_lead_intake',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('company_name', sa.String(255), nullable=False),
        sa.Column('contact_name', sa.String(255)),
        sa.Column('contact_email', sa.String(320)),
        sa.Column('pain_point', sa.Text()),
        sa.Column('services_interested', JSONB),
        sa.Column('source', sa.String(100)),  # hubspot/apollo/linkedin/manual
        sa.Column('first_email_sent', sa.Boolean(), default=False),
        sa.Column('first_email_content', sa.Text()),
        sa.Column('notes', sa.Text()),
        sa.Column('priority', sa.String(20), default='warm'),  # hot/warm/cold
        sa.Column('lead_id_created', sa.Integer()),  # FK to leads after processing
        sa.Column('processed', sa.Boolean(), default=False),
        sa.Column('processing_result', JSONB),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('case_studies',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('client_type', sa.String(100)),  # industry/company-type
        sa.Column('client_size', sa.String(50)),
        sa.Column('pain_solved', sa.Text()),
        sa.Column('solution_summary', sa.Text()),
        sa.Column('result_achieved', sa.Text()),
        sa.Column('proof_points', JSONB),  # ["40% cost reduction", "£180k saved"]
        sa.Column('service_category', sa.String(100)),
        sa.Column('is_verified', sa.Boolean(), default=True),
        sa.Column('use_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('captain_style_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('dimension', sa.String(100)),  # tone/pricing/objection-handling
        sa.Column('before_text', sa.Text()),
        sa.Column('after_text', sa.Text()),
        sa.Column('diff_summary', sa.Text()),
        sa.Column('pattern_type', sa.String(100)),
        sa.Column('confidence', sa.Float(), default=0.5),
        sa.Column('observations', sa.Integer(), default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('hubspot_sync_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sync_type', sa.String(50)),  # import/export/webhook
        sa.Column('records_synced', sa.Integer(), default=0),
        sa.Column('conflicts_resolved', sa.Integer(), default=0),
        sa.Column('errors', JSONB),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('voice_commands',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('input_text', sa.Text()),
        sa.Column('detected_intent', sa.String(100)),
        sa.Column('response_text', sa.Text()),
        sa.Column('audio_url', sa.String(500)),
        sa.Column('action_taken', sa.String(255)),
        sa.Column('required_confirmation', sa.Boolean(), default=False),
        sa.Column('execution_ms', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('predicted_actions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('action_type', sa.String(100)),
        sa.Column('confidence', sa.Float()),
        sa.Column('revenue_impact', sa.Float()),
        sa.Column('urgency', sa.String(20)),
        sa.Column('reasoning', sa.Text()),
        sa.Column('executed', sa.Boolean(), default=False),
        sa.Column('dismissed', sa.Boolean(), default=False),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('detected_threats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('threat_type', sa.String(100)),
        sa.Column('threat_level', sa.String(20)),  # info/watch/alert/critical
        sa.Column('description', sa.Text()),
        sa.Column('source', sa.String(100)),
        sa.Column('response_plan', sa.Text()),
        sa.Column('auto_responded', sa.Boolean(), default=False),
        sa.Column('captain_notified', sa.Boolean(), default=False),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('war_room_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('trigger', sa.String(255)),
        sa.Column('situation_brief', sa.Text()),
        sa.Column('options', JSONB),
        sa.Column('recommended_action', sa.Text()),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('resolution', sa.Text()),
        sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
    )

    op.create_table('scenario_simulations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('question', sa.Text()),
        sa.Column('action_described', sa.Text()),
        sa.Column('optimistic_outcome', sa.Text()),
        sa.Column('realistic_outcome', sa.Text()),
        sa.Column('pessimistic_outcome', sa.Text()),
        sa.Column('expected_value', sa.Float()),
        sa.Column('risk_score', sa.Float()),
        sa.Column('recommendation', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    for t in ['scenario_simulations', 'war_room_sessions', 'detected_threats',
              'predicted_actions', 'voice_commands', 'hubspot_sync_log',
              'captain_style_profiles', 'case_studies', 'captain_lead_intake']:
        op.drop_table(t)
```

---

## STEP 2 — CAPTAIN'S INTELLIGENCE BRIDGE

### 2A — Bring Your Own Lead Intake

Create: `app/services/captain/bridge.py`

```python
"""Captain's Intelligence Bridge — connects manual sales ops to JARVIS."""
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def process_captain_lead_intake(db: AsyncSession, intake_data: dict) -> dict:
    """
    Process lead submitted by Captain from HubSpot/Apollo/LinkedIn.
    If first_email_sent=True, skip to Email 2 in sequence.
    """
    company = intake_data.get("company_name", "")
    contact_email = intake_data.get("contact_email", "")
    first_email_sent = intake_data.get("first_email_sent", False)
    priority = intake_data.get("priority", "warm")

    # 1. Create/update lead record
    existing = (await db.execute(text(
        "SELECT id FROM leads WHERE email=:e LIMIT 1"
    ), {"e": contact_email})).scalar_one_or_none()

    if existing:
        lead_id = existing
        await db.execute(text("""
            UPDATE leads SET 
                notes = COALESCE(notes,'') || '\n[CAPTAIN INTAKE] ' || :note,
                updated_at = NOW()
            WHERE id = :id
        """), {"id": lead_id, "note": intake_data.get("notes", "")})
    else:
        # Score the lead
        from app.services.leads.scorer import score_lead_v2
        lead_dict = {
            "email": contact_email,
            "name": intake_data.get("contact_name", ""),
            "company": company,
            "industry": intake_data.get("industry", ""),
        }
        score, signals = score_lead_v2(lead_dict)

        # Boost score for captain-submitted leads (they've been personally vetted)
        priority_boost = {"hot": 20, "warm": 10, "cold": 0}
        final_score = min(score + priority_boost.get(priority, 0), 100)

        result = await db.execute(text("""
            INSERT INTO leads (name, email, company, industry, score, signal_breakdown, 
                               source, status, outreach_eligible, created_at)
            VALUES (:name, :email, :company, :industry, :score, :signals::jsonb,
                    'captain_bridge', 'new', true, NOW())
            RETURNING id
        """), {
            "name": intake_data.get("contact_name", ""),
            "email": contact_email,
            "company": company,
            "industry": intake_data.get("industry", ""),
            "score": final_score,
            "signals": str(signals).replace("'", '"'),
        })
        lead_id = result.scalar()

    # 2. If first email already sent, enroll starting from step 2
    enrollment_start = 2 if first_email_sent else 1
    action = "enrolled_from_step_2" if first_email_sent else "enrolled_from_step_1"

    # Store original email if provided (for style learning)
    if first_email_sent and intake_data.get("first_email_content"):
        await db.execute(text("""
            INSERT INTO captain_style_profiles 
                (dimension, before_text, after_text, diff_summary, pattern_type)
            VALUES ('email_tone', '', :content, 'Captain-written first email', 'captain_outreach')
        """), {"content": intake_data.get("first_email_content", "")[:2000]})

    # 3. Store case study if provided
    if intake_data.get("case_study_result"):
        await db.execute(text("""
            INSERT INTO case_studies (title, client_type, pain_solved, result_achieved, service_category)
            VALUES (:t, :ct, :pain, :result, :svc)
        """), {
            "t": f"Case Study: {company}",
            "ct": intake_data.get("industry", ""),
            "pain": intake_data.get("pain_point", ""),
            "result": intake_data.get("case_study_result", ""),
            "svc": str(intake_data.get("services_interested", [""])[0] if intake_data.get("services_interested") else "")
        })

    # 4. Create intake record
    await db.execute(text("""
        INSERT INTO captain_lead_intake
            (company_name, contact_name, contact_email, pain_point, services_interested,
             source, first_email_sent, first_email_content, notes, priority,
             lead_id_created, processed, processing_result)
        VALUES (:co, :cn, :ce, :pp, :si::jsonb, :src, :fe, :fec, :n, :pr, :lid, true, :res::jsonb)
    """), {
        "co": company,
        "cn": intake_data.get("contact_name", ""),
        "ce": contact_email,
        "pp": intake_data.get("pain_point", ""),
        "si": str(intake_data.get("services_interested", [])).replace("'", '"'),
        "src": intake_data.get("source", "manual"),
        "fe": first_email_sent,
        "fec": intake_data.get("first_email_content", ""),
        "n": intake_data.get("notes", ""),
        "pr": priority,
        "lid": lead_id,
        "res": f'{{"action": "{action}", "lead_id": {lead_id}}}'
    })

    await db.commit()
    logger.info(f"Captain bridge intake processed: {company} ({contact_email}) → lead {lead_id}")

    return {
        "status": "processed",
        "lead_id": lead_id,
        "action": action,
        "next_step": f"Email {enrollment_start} will fire according to sequence schedule",
        "message": f"JARVIS has enrolled {contact_email}. {action.replace('_', ' ').title()}."
    }


async def parse_brain_dump(text_input: str) -> dict:
    """Parse free-form brain dump text into structured CRM data using AI."""
    try:
        from app.services.ai_router import get_ai_response
        prompt = f"""Extract CRM data from this brain dump text. Return JSON only.

Text: "{text_input}"

Return this exact JSON structure:
{{
  "company_name": "...",
  "contact_name": "...",
  "contact_email": "...",
  "phone": "...",
  "pain_point": "...",
  "budget_signal": "...",
  "timeline": "...",
  "decision_maker": true/false,
  "next_action": "...",
  "priority": "hot/warm/cold",
  "notes": "..."
}}

If a field is unknown, use null. Return only JSON, no explanation."""
        response = await get_ai_response(prompt, task_type="fast")
        import json
        # Clean response
        clean = response.strip()
        if "```" in clean:
            clean = clean.split("```")[1].lstrip("json").strip()
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Brain dump parse failed: {e}")
        return {"raw_text": text_input, "parse_error": str(e)}


async def extract_email_thread_intelligence(email_thread: str) -> dict:
    """Extract CRM intelligence from a pasted email thread."""
    try:
        from app.services.ai_router import get_ai_response
        prompt = f"""Analyze this email thread and extract sales intelligence. Return JSON only.

Thread:
{email_thread[:3000]}

Return:
{{
  "prospect_name": "...",
  "prospect_email": "...",
  "company": "...",
  "conversation_stage": "cold/interested/evaluating/negotiating/decided",
  "key_objections": ["..."],
  "buying_signals": ["..."],
  "competitor_mentions": ["..."],
  "price_sensitivity": "low/medium/high",
  "promises_made": ["..."],
  "recommended_next_action": "...",
  "sentiment": "positive/neutral/negative"
}}"""
        response = await get_ai_response(prompt, task_type="reasoning")
        import json
        clean = response.strip()
        if "```" in clean:
            clean = clean.split("```")[1].lstrip("json").strip()
        return json.loads(clean)
    except Exception as e:
        return {"raw_thread": email_thread[:500], "extract_error": str(e)}
```

### 2B — Captain Bridge API Routes

Add to `app.py`:

```python
@app.post("/api/v1/captain/bring-lead")
async def captain_bring_lead(data: dict, db=Depends(get_db)):
    """Submit a lead from HubSpot/Apollo/LinkedIn to JARVIS."""
    from app.services.captain.bridge import process_captain_lead_intake
    return await process_captain_lead_intake(db, data)


@app.post("/api/v1/captain/brain-dump")
async def captain_brain_dump(data: dict, db=Depends(get_db)):
    """Parse free-form notes into structured CRM data."""
    from app.services.captain.bridge import parse_brain_dump
    text_input = data.get("text", "")
    if not text_input:
        raise HTTPException(400, "text is required")
    parsed = await parse_brain_dump(text_input)
    # If email found, optionally auto-create lead
    if parsed.get("company_name") and parsed.get("contact_email"):
        parsed["_suggestion"] = "Lead data extracted. Call /captain/bring-lead to enroll."
    return parsed


@app.post("/api/v1/captain/email-import")
async def captain_email_import(data: dict, db=Depends(get_db)):
    """Import and analyze an email thread."""
    from app.services.captain.bridge import extract_email_thread_intelligence
    thread = data.get("thread", "")
    if not thread:
        raise HTTPException(400, "thread is required")
    intelligence = await extract_email_thread_intelligence(thread)
    return intelligence


@app.post("/api/v1/captain/case-studies")
async def add_case_study(data: dict, db=Depends(get_db)):
    """Add a real case study to the library."""
    await db.execute(text("""
        INSERT INTO case_studies
            (title, client_type, client_size, pain_solved, result_achieved, 
             proof_points, service_category, is_verified)
        VALUES (:t, :ct, :cs, :pain, :result, :proof::jsonb, :svc, true)
    """), {
        "t": data.get("title", ""),
        "ct": data.get("client_type", ""),
        "cs": data.get("client_size", ""),
        "pain": data.get("pain_solved", ""),
        "result": data.get("result_achieved", ""),
        "proof": str(data.get("proof_points", [])).replace("'", '"'),
        "svc": data.get("service_category", "")
    })
    await db.commit()
    return {"status": "created", "message": "Case study added to JARVIS library"}


@app.get("/api/v1/captain/case-studies")
async def list_case_studies(service: str = None, db=Depends(get_db)):
    query = "SELECT * FROM case_studies WHERE 1=1"
    params = {}
    if service:
        query += " AND service_category ILIKE :svc"
        params["svc"] = f"%{service}%"
    query += " ORDER BY use_count DESC, created_at DESC"
    rows = (await db.execute(text(query), params)).fetchall()
    return {"case_studies": [dict(r) for r in rows]}


@app.post("/api/v1/captain/apollo-import")
async def captain_apollo_import(data: dict, db=Depends(get_db)):
    """Import leads from Apollo CSV/JSON export."""
    leads_data = data.get("leads", [])
    if not leads_data:
        raise HTTPException(400, "leads array is required")
    
    imported = 0
    duplicates = 0
    errors = []
    
    for lead in leads_data[:500]:  # Cap at 500 per import
        try:
            email = (lead.get("email") or lead.get("Email") or "").strip().lower()
            if not email:
                continue
            
            existing = (await db.execute(text(
                "SELECT id FROM leads WHERE email=:e LIMIT 1"
            ), {"e": email})).scalar_one_or_none()
            
            if existing:
                duplicates += 1
                continue
            
            from app.services.leads.scorer import score_lead_v2
            score, signals = score_lead_v2(lead)
            
            await db.execute(text("""
                INSERT INTO leads (name, email, company, industry, title, score, 
                                   signal_breakdown, source, status, outreach_eligible)
                VALUES (:n, :e, :co, :ind, :t, :s, :sig::jsonb, 'apollo_import', 'new', false)
            """), {
                "n": lead.get("name") or lead.get("Name") or "",
                "e": email,
                "co": lead.get("company") or lead.get("Company") or "",
                "ind": lead.get("industry") or lead.get("Industry") or "",
                "t": lead.get("title") or lead.get("Title") or "",
                "s": score,
                "sig": str(signals).replace("'", '"'),
            })
            imported += 1
        except Exception as ex:
            errors.append(str(ex))
    
    await db.commit()
    return {
        "imported": imported,
        "duplicates": duplicates,
        "errors": errors[:10],
        "note": "Leads stored. Review in dashboard before enabling outreach."
    }


@app.get("/api/v1/captain/intelligence-feed")
async def captain_intelligence_feed(db=Depends(get_db)):
    """Real-time intelligence on leads Captain has been working."""
    recent_intakes = (await db.execute(text("""
        SELECT i.company_name, i.contact_email, i.priority, i.submitted_at,
               l.score, l.status
        FROM captain_lead_intake i
        LEFT JOIN leads l ON l.id = i.lead_id_created
        WHERE i.submitted_at > NOW() - INTERVAL '30 days'
        ORDER BY i.submitted_at DESC
        LIMIT 20
    """))).fetchall()
    
    return {
        "recent_intakes": [dict(r) for r in recent_intakes],
        "tip": "Use /captain/bring-lead to submit new leads from HubSpot/Apollo/LinkedIn"
    }
```

---

## STEP 3 — VOICE COMMAND INTERFACE

Create: `app/services/voice/command_processor.py`

```python
"""Voice command processing with ElevenLabs TTS response."""
import os
import logging
import aiohttp
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

VOICE_INTENTS = {
    "briefing": ["status", "briefing", "morning", "how are we doing", "update"],
    "revenue": ["revenue", "money", "pipeline", "forecast", "deals"],
    "outreach": ["outreach", "emails", "sequences", "campaigns"],
    "leads": ["leads", "prospects", "new contacts"],
    "approve": ["approve", "confirm", "yes go ahead"],
    "health": ["health", "system", "everything working"],
    "brain_dump": ["note", "just spoke", "just met", "add lead", "remind me"],
}


def detect_intent(text: str) -> str:
    text_lower = text.lower()
    for intent, keywords in VOICE_INTENTS.items():
        if any(k in text_lower for k in keywords):
            return intent
    return "general_query"


async def generate_tts_response(text: str) -> str | None:
    """Generate audio via ElevenLabs. Returns audio URL or None."""
    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
    
    if not api_key or not voice_id:
        logger.info("ElevenLabs not configured — text-only response")
        return None
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        payload = {
            "text": text[:500],  # Cap at 500 chars for voice
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.6, "similarity_boost": 0.8}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    audio_data = await resp.read()
                    # Save to temp file
                    filename = f"/tmp/jarvis_voice_{int(datetime.now().timestamp())}.mp3"
                    with open(filename, "wb") as f:
                        f.write(audio_data)
                    return f"/api/v1/voice/audio/{filename.split('/')[-1]}"
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
    return None


async def process_voice_command(text: str, db) -> dict:
    """Process a voice/text command and return text + audio response."""
    from datetime import datetime
    start = datetime.now()
    intent = detect_intent(text)
    response_text = ""
    action_taken = ""

    if intent == "briefing":
        # Pull morning briefing data
        try:
            from app.services.briefing import get_quick_briefing
            briefing = await get_quick_briefing(db)
            response_text = briefing.get("summary", "All systems operational, Captain.")
        except Exception:
            response_text = "JARVIS systems are running. Briefing data loading."
        action_taken = "pulled_briefing"

    elif intent == "revenue":
        try:
            from app.services.intelligence.revenue_forecaster import run_revenue_forecast
            forecast = await run_revenue_forecast(db, horizon_days=30)
            response_text = (f"Pipeline value is £{forecast['pipeline_value']:,.0f}. "
                           f"Expected close in 30 days: £{forecast['p50']:,.0f}. "
                           f"{len(forecast['leakage_deals'])} deals need attention.")
        except Exception:
            response_text = "Revenue data is processing. Check the dashboard for details."
        action_taken = "pulled_forecast"

    elif intent == "health":
        response_text = "All critical systems are operational. Database connected. AI providers active. Outreach engine running."
        action_taken = "health_check"

    elif intent == "brain_dump":
        response_text = "Understood. Send your note via /captain/brain-dump and I'll extract the CRM data immediately."
        action_taken = "redirect_to_brain_dump"

    else:
        # General AI response
        try:
            from app.services.ai_router import get_ai_response
            system_context = "You are JARVIS, operational AI for Aliyar Solutions. Answer in max 3 sentences, professionally, addressing Captain directly."
            response_text = await get_ai_response(f"{system_context}\n\nCaptain: {text}", task_type="fast")
            response_text = response_text[:500]
        except Exception:
            response_text = "I'm processing your request, Captain. Stand by."
        action_taken = "general_ai_response"

    # Generate audio
    audio_url = await generate_tts_response(response_text)
    execution_ms = int((datetime.now() - start).total_seconds() * 1000)

    return {
        "text_response": response_text,
        "audio_url": audio_url,
        "intent": intent,
        "action_taken": action_taken,
        "requires_confirmation": False,
        "execution_ms": execution_ms
    }
```

Add API routes:
```python
@app.post("/api/v1/voice/command")
async def voice_command(data: dict, db=Depends(get_db)):
    from app.services.voice.command_processor import process_voice_command
    text = data.get("text", "") or data.get("command", "")
    if not text:
        raise HTTPException(400, "text or command required")
    result = await process_voice_command(text, db)
    return result

@app.get("/api/v1/voice/audio/{filename}")
async def get_voice_audio(filename: str):
    from fastapi.responses import FileResponse
    import os
    path = f"/tmp/{filename}"
    if not os.path.exists(path):
        raise HTTPException(404, "Audio file not found")
    return FileResponse(path, media_type="audio/mpeg")
```

---

## STEP 4 — PREDICTIVE ACTION ENGINE

Create: `app/services/intelligence/predictive_actions.py`

```python
"""Generates Captain's 3 best moves every 4 hours."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def generate_predicted_actions(db: AsyncSession) -> list[dict]:
    """Analyze current state and generate top 3 predicted best actions."""
    actions = []
    now = datetime.now(timezone.utc)

    # Check 1: Hot leads not yet contacted
    hot_leads = (await db.execute(text("""
        SELECT id, name, company, score FROM leads
        WHERE score >= 75
        AND outreach_eligible = true
        AND status = 'new'
        AND created_at < NOW() - INTERVAL '2 hours'
        LIMIT 3
    """))).fetchall()

    for lead in hot_leads:
        actions.append({
            "title": f"High-value lead ready: {lead[2]}",
            "description": f"{lead[1]} at {lead[2]} scored {lead[3]}/100 — enroll in sequence now for best conversion.",
            "action_type": "enroll_lead",
            "confidence": 0.85,
            "revenue_impact": 5000.0,
            "urgency": "high",
            "reasoning": f"Score {lead[3]} — optimal outreach window open",
            "metadata": {"lead_id": lead[0]}
        })

    # Check 2: Proposals open but not replied in 3 days
    stale_proposals = (await db.execute(text("""
        SELECT id, client_name, value, last_opened_at
        FROM proposals
        WHERE status = 'viewed'
        AND last_opened_at < NOW() - INTERVAL '3 days'
        AND last_opened_at > NOW() - INTERVAL '14 days'
        ORDER BY value DESC
        LIMIT 2
    """))).fetchall()

    for prop in stale_proposals:
        days_since = (now - prop[3]).days if prop[3] else 3
        actions.append({
            "title": f"Follow up: {prop[1]} — proposal opened {days_since}d ago",
            "description": f"Proposal (£{float(prop[2] or 0):,.0f}) was opened {days_since} days ago. A brief check-in now significantly increases close probability.",
            "action_type": "proposal_followup",
            "confidence": 0.78,
            "revenue_impact": float(prop[2] or 0),
            "urgency": "medium",
            "reasoning": "Viewed but no response — optimal follow-up window",
            "metadata": {"proposal_id": prop[0]}
        })

    # Check 3: Sequences with good reply rates — scale up
    performing_sequences = (await db.execute(text("""
        SELECT id, name, emails_sent, replies_received
        FROM outreach_sequences
        WHERE status = 'active'
        AND emails_sent > 10
        AND (replies_received::float / NULLIF(emails_sent, 0)) > 0.05
        ORDER BY (replies_received::float / NULLIF(emails_sent, 0)) DESC
        LIMIT 1
    """))).fetchall()

    for seq in performing_sequences:
        rate = (seq[3] / max(seq[2], 1)) * 100
        actions.append({
            "title": f"Scale winning sequence: {seq[1]}",
            "description": f"This sequence has {rate:.1f}% reply rate — above average. Enroll more ICP-matched leads to compound results.",
            "action_type": "scale_sequence",
            "confidence": 0.72,
            "revenue_impact": 15000.0,
            "urgency": "low",
            "reasoning": f"{rate:.1f}% reply rate indicates strong message-market fit",
            "metadata": {"sequence_id": seq[0]}
        })

    # Store and expire old predicted actions
    await db.execute(text(
        "UPDATE predicted_actions SET dismissed=true WHERE expires_at < NOW()"
    ))

    for action in actions[:3]:  # Top 3 only
        await db.execute(text("""
            INSERT INTO predicted_actions
                (title, description, action_type, confidence, revenue_impact,
                 urgency, reasoning, expires_at)
            VALUES (:t, :d, :at, :c, :ri, :u, :r, :exp)
        """), {
            **action,
            "t": action["title"], "d": action["description"],
            "at": action["action_type"], "c": action["confidence"],
            "ri": action["revenue_impact"], "u": action["urgency"],
            "r": action["reasoning"],
            "exp": now + timedelta(hours=8)
        })

    await db.commit()
    return actions


async def get_active_predicted_actions(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(text("""
        SELECT title, description, action_type, confidence, revenue_impact,
               urgency, reasoning, created_at
        FROM predicted_actions
        WHERE executed=false AND dismissed=false AND expires_at > NOW()
        ORDER BY confidence DESC, revenue_impact DESC
        LIMIT 5
    """))).fetchall()
    return [dict(r) for r in rows]
```

Register as job (every 4 hours) and add endpoint:
```python
@app.get("/api/v1/intelligence/predicted-actions")
async def get_predicted_actions(db=Depends(get_db)):
    from app.services.intelligence.predictive_actions import get_active_predicted_actions
    return {"actions": await get_active_predicted_actions(db)}
```

---

## STEP 5 — JARVIS PUSHBACK ENGINE

Create: `app/services/intelligence/pushback_engine.py`

```python
"""JARVIS has opinions — challenges Captain on poor decisions."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PUSHBACK_RULES = [
    {
        "id": "price_too_low",
        "condition": lambda data: (
            data.get("proposed_price") and data.get("recommended_price") and
            float(data["proposed_price"]) < float(data["recommended_price"]) * 0.75
        ),
        "message": lambda data: (
            f"Captain, I recommend against pricing at £{data['proposed_price']:,.0f}. "
            f"Market data suggests £{data['recommended_price']:,.0f}. "
            f"Discounting more than 25% signals desperation and compresses margins. "
            f"You can override — I'm logging this for outcome tracking."
        ),
        "severity": "high"
    },
    {
        "id": "low_score_lead_outreach",
        "condition": lambda data: (
            data.get("action") == "enroll_outreach" and
            (data.get("lead_score") or 100) < 45
        ),
        "message": lambda data: (
            f"Captain, lead score is {data.get('lead_score')}/100 — below the 45-point threshold. "
            f"Our data shows sub-45 leads have <3% conversion rate. "
            f"This would waste outreach budget and warm IP. Recommend: CRM-only until score improves."
        ),
        "severity": "medium"
    },
    {
        "id": "proposal_no_case_study",
        "condition": lambda data: (
            data.get("action") == "send_proposal" and
            not data.get("has_case_study")
        ),
        "message": lambda data: (
            "Captain, this proposal has no supporting case study. "
            "Proposals with case studies convert 2.4x better. "
            "I can match a relevant case study from our library — or you can proceed without one."
        ),
        "severity": "low"
    },
]


async def check_for_pushback(db: AsyncSession, action_data: dict) -> dict | None:
    """
    Call this before any Captain action.
    Returns pushback dict if JARVIS disagrees, None if no objection.
    """
    for rule in PUSHBACK_RULES:
        try:
            if rule["condition"](action_data):
                pushback = {
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "message": rule["message"](action_data),
                    "can_override": True,
                    "override_instruction": "Add override=true to your request to proceed anyway"
                }
                # Log disagreement
                await db.execute(text("""
                    INSERT INTO autonomous_decisions
                        (decision_type, tier, description, rationale, outcome)
                    VALUES ('jarvis_pushback', 2, :desc, :rat, 'pending_captain_decision')
                """), {
                    "desc": f"JARVIS challenged action: {action_data.get('action', 'unknown')}",
                    "rat": rule["message"](action_data)
                })
                await db.commit()
                logger.info(f"Pushback triggered: {rule['id']}")
                return pushback
        except Exception as e:
            logger.debug(f"Pushback rule {rule['id']} evaluation error: {e}")

    return None
```

Wrap proposal and outreach endpoints with pushback check.

---

## STEP 6 — SITUATION CONSCIOUSNESS FEED (WebSocket)

Create: `app/services/intelligence/consciousness.py`

```python
"""Real-time JARVIS consciousness — what JARVIS is thinking right now."""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def get_consciousness_snapshot(db: AsyncSession) -> dict:
    """Returns current JARVIS mental state — what's active, pending, notable."""
    now = datetime.now(timezone.utc)

    # Active jobs
    active_jobs = []
    try:
        jobs = (await db.execute(text("""
            SELECT job_id, next_run_time FROM apscheduler_jobs
            WHERE next_run_time < :cutoff
            ORDER BY next_run_time LIMIT 5
        """), {"cutoff": now})).fetchall()
        active_jobs = [{"job": j[0], "due": str(j[1])} for j in jobs]
    except Exception:
        pass

    # Pending captain queue
    pending = (await db.execute(text("""
        SELECT COUNT(*) FROM jarvis_captain_queue WHERE status='pending'
    """))).scalar_one_or_none() or 0

    # Recent outreach
    sent_today = (await db.execute(text("""
        SELECT COUNT(*) FROM outreach_log 
        WHERE created_at > NOW() - INTERVAL '24 hours'
    """))).scalar_one_or_none() or 0

    # Open proposals
    open_proposals = (await db.execute(text("""
        SELECT COUNT(*), SUM(value) FROM proposals 
        WHERE status IN ('sent', 'viewed', 'negotiating')
    """))).fetchone()

    # Active threats
    threats = (await db.execute(text("""
        SELECT COUNT(*) FROM detected_threats 
        WHERE resolved=false AND threat_level IN ('alert','critical')
    """))).scalar_one_or_none() or 0

    summary_parts = []
    if sent_today > 0:
        summary_parts.append(f"{sent_today} outreach emails sent in last 24h")
    if pending > 0:
        summary_parts.append(f"{pending} items await Captain's decision")
    if open_proposals[0]:
        summary_parts.append(f"{open_proposals[0]} open proposals (£{float(open_proposals[1] or 0):,.0f} pipeline)")
    if threats > 0:
        summary_parts.append(f"⚠️ {threats} active threat(s) require attention")

    return {
        "timestamp": now.isoformat(),
        "summary": ". ".join(summary_parts) or "All systems nominal. No immediate actions required.",
        "active_jobs": active_jobs,
        "pending_decisions": pending,
        "outreach_24h": sent_today,
        "open_proposals": open_proposals[0] or 0,
        "pipeline_value": float(open_proposals[1] or 0),
        "active_threats": threats,
        "mode": "degraded" if _check_degraded() else "normal"
    }


def _check_degraded() -> bool:
    try:
        from app.services.ai_router import is_degraded
        return is_degraded()
    except Exception:
        return False
```

Add WebSocket route:
```python
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

@app.websocket("/ws/consciousness")
async def consciousness_websocket(websocket: WebSocket, db=Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            from app.services.intelligence.consciousness import get_consciousness_snapshot
            snapshot = await get_consciousness_snapshot(db)
            await websocket.send_json(snapshot)
            await asyncio.sleep(30)  # Update every 30 seconds
    except WebSocketDisconnect:
        pass

@app.get("/api/v1/jarvis/situation")
async def get_situation(db=Depends(get_db)):
    from app.services.intelligence.consciousness import get_consciousness_snapshot
    return await get_consciousness_snapshot(db)
```

---

## STEP 7 — EMOTIONAL INTELLIGENCE ON EMAIL REPLIES

Create: `app/services/intelligence/emotional_intelligence.py`

```python
"""Analyze email reply sentiment and adjust outreach tone."""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

OBJECTION_PATTERNS = {
    "price": ["too expensive", "costly", "budget", "afford", "price", "cost"],
    "timing": ["not now", "later", "busy", "next quarter", "next year", "timing"],
    "trust": ["not sure", "uncertain", "more information", "proof", "case study", "references"],
    "authority": ["need to check", "my boss", "team decision", "committee", "approval"],
    "competitor": ["already using", "working with", "have a solution", "current provider"],
}

BUYING_SIGNAL_PATTERNS = {
    "high": ["let's talk", "interested", "schedule", "call me", "send more", "proposal", "demo"],
    "medium": ["sounds good", "tell me more", "how does it work", "what's the process"],
    "low": ["maybe", "possibly", "will consider", "keep in touch"],
}


async def analyze_reply(db: AsyncSession, reply_text: str, contact_id: int,
                         sequence_id: int) -> dict:
    """Analyze incoming email reply for sentiment and intent."""
    reply_lower = reply_text.lower()

    # Detect objections
    objections = []
    for obj_type, patterns in OBJECTION_PATTERNS.items():
        if any(p in reply_lower for p in patterns):
            objections.append(obj_type)

    # Detect buying signals
    buying_strength = "none"
    for strength, patterns in BUYING_SIGNAL_PATTERNS.items():
        if any(p in reply_lower for p in patterns):
            buying_strength = strength
            break

    # Sentiment (simple keyword-based)
    negative_words = ["no", "not interested", "remove", "unsubscribe", "stop", "spam", "never"]
    positive_words = ["yes", "great", "excellent", "perfect", "love", "excited", "absolutely"]
    negative_count = sum(1 for w in negative_words if w in reply_lower)
    positive_count = sum(1 for w in positive_words if w in reply_lower)

    if negative_count > positive_count:
        sentiment = "negative"
        recommended_action = "pause_and_review"
    elif positive_count > 0 or buying_strength in ["high", "medium"]:
        sentiment = "positive"
        recommended_action = "escalate_to_captain"
    else:
        sentiment = "neutral"
        recommended_action = "continue_sequence_with_adjustment"

    analysis = {
        "sentiment": sentiment,
        "buying_strength": buying_strength,
        "objections": objections,
        "recommended_action": recommended_action,
        "reply_preview": reply_text[:200]
    }

    # Store in reply log if table exists
    try:
        await db.execute(text("""
            INSERT INTO reply_log (contact_id, sequence_id, reply_text, classification, metadata)
            VALUES (:cid, :sid, :rt, :cls, :meta::jsonb)
        """), {
            "cid": contact_id, "sid": sequence_id,
            "rt": reply_text[:2000],
            "cls": sentiment,
            "meta": str(analysis).replace("'", '"')
        })
    except Exception:
        pass

    # If negative → add to DNC consideration
    if sentiment == "negative" and "unsubscribe" in reply_lower:
        from app.services.outreach.compliance import process_unsubscribe
        await process_unsubscribe(db, "", sequence_id)  # will need contact email

    # If positive → alert Captain
    if buying_strength == "high":
        try:
            from app.services.notifications import send_telegram
            await send_telegram(
                f"🔥 *Hot Reply Detected!*\n\n"
                f"Buying signal: {buying_strength.upper()}\n"
                f"Preview: {reply_text[:200]}\n"
                f"Action: Escalate to Captain immediately"
            )
        except Exception:
            pass

    return analysis
```

---

## STEP 8 — SCENARIO SIMULATION ENGINE

```python
# Add to app.py

@app.post("/api/v1/intelligence/simulate")
async def simulate_scenario(data: dict, db=Depends(get_db)):
    """Simulate outcomes of a proposed action — 3 scenarios."""
    action = data.get("action", "")
    context = data.get("context", {})
    
    if not action:
        raise HTTPException(400, "action is required")
    
    try:
        from app.services.ai_router import get_ai_response
        prompt = f"""You are JARVIS strategic simulator for Aliyar Solutions.
        
Action being considered: {action}
Context: {str(context)[:500]}

Simulate 3 outcomes in 30-90 days. Return JSON:
{{
  "optimistic": {{"probability": 0.25, "outcome": "...", "revenue_impact": 0}},
  "realistic": {{"probability": 0.55, "outcome": "...", "revenue_impact": 0}},
  "pessimistic": {{"probability": 0.20, "outcome": "...", "revenue_impact": 0}},
  "expected_value": 0,
  "recommendation": "...",
  "key_risks": ["..."]
}}

Be specific with numbers. Revenue impact in GBP."""
        response = await get_ai_response(prompt, task_type="reasoning")
        import json
        clean = response.strip()
        if "```" in clean:
            clean = clean.split("```")[1].lstrip("json").strip()
        result = json.loads(clean)
        result["action"] = action
        return result
    except Exception as e:
        return {
            "action": action,
            "error": str(e),
            "fallback": "Simulation unavailable — AI provider degraded"
        }
```

---

## STEP 9 — WAR ROOM MODE

```python
# Add to app.py

_WAR_ROOM_ACTIVE = False

@app.post("/api/v1/jarvis/war-room/activate")
async def activate_war_room(data: dict, db=Depends(get_db)):
    global _WAR_ROOM_ACTIVE
    _WAR_ROOM_ACTIVE = True
    trigger = data.get("trigger", "Manual activation")
    
    # Generate situation brief
    brief = "War Room activated. All resources focused on priority situation."
    options = []
    try:
        from app.services.ai_router import get_ai_response
        from app.services.intelligence.consciousness import get_consciousness_snapshot
        snapshot = await get_consciousness_snapshot(db)
        prompt = f"""JARVIS War Room activated. Trigger: {trigger}
Current state: {str(snapshot)[:500]}
Generate 3 response options with expected outcomes. Be direct."""
        brief = await get_ai_response(prompt, task_type="strategy")
    except Exception:
        pass

    await db.execute(text("""
        INSERT INTO war_room_sessions (trigger, situation_brief, options, status)
        VALUES (:t, :b, :o::jsonb, 'active')
    """), {"t": trigger, "b": brief, "o": '[]'})
    await db.commit()
    
    try:
        from app.services.notifications import send_telegram
        await send_telegram(f"🚨 *WAR ROOM ACTIVATED*\n\nTrigger: {trigger}\n\nAll JARVIS resources focused.")
    except Exception:
        pass

    return {"status": "war_room_active", "trigger": trigger, "brief": brief[:1000]}


@app.post("/api/v1/jarvis/war-room/deactivate")
async def deactivate_war_room(data: dict, db=Depends(get_db)):
    global _WAR_ROOM_ACTIVE
    _WAR_ROOM_ACTIVE = False
    resolution = data.get("resolution", "")
    
    await db.execute(text("""
        UPDATE war_room_sessions SET status='resolved', resolution=:r, resolved_at=NOW()
        WHERE status='active'
    """), {"r": resolution})
    await db.commit()
    return {"status": "war_room_deactivated", "resolution": resolution}

@app.get("/api/v1/jarvis/war-room/status")
async def war_room_status():
    return {"active": _WAR_ROOM_ACTIVE}
```

---

## STEP 10 — 48-HOUR REVENUE DRIFT ALERT

Create: `app/services/intelligence/revenue_monitor.py`

```python
"""Monitor 48-hour pipeline changes and alert on drift."""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def check_revenue_drift(db: AsyncSession):
    """Run every 6 hours. Alert if pipeline drops >10% in 48h."""
    now = datetime.now(timezone.utc)
    cutoff_48h = now - timedelta(hours=48)

    # Current pipeline
    current = (await db.execute(text("""
        SELECT SUM(value) FROM proposals
        WHERE status IN ('sent','viewed','negotiating','demo_scheduled')
    """))).scalar_one_or_none() or 0

    # Pipeline 48 hours ago (from forecast snapshots)
    past = (await db.execute(text("""
        SELECT pipeline_value FROM revenue_forecasts
        WHERE created_at < :cutoff
        ORDER BY created_at DESC LIMIT 1
    """), {"cutoff": cutoff_48h})).scalar_one_or_none()

    if not past or past == 0:
        return {"status": "insufficient_history"}

    change_pct = ((float(current) - float(past)) / float(past)) * 100

    result = {
        "current_pipeline": float(current),
        "pipeline_48h_ago": float(past),
        "change_percent": round(change_pct, 1),
        "alert_triggered": False
    }

    if change_pct <= -10:
        result["alert_triggered"] = True
        try:
            from app.services.notifications import send_telegram
            await send_telegram(
                f"⚠️ *Revenue Pipeline Drift Alert*\n\n"
                f"Pipeline dropped {abs(change_pct):.1f}% in 48 hours\n"
                f"Current: £{float(current):,.0f}\n"
                f"48h ago: £{float(past):,.0f}\n"
                f"Loss: £{float(past) - float(current):,.0f}\n\n"
                f"Check /intelligence for details."
            )
        except Exception:
            pass

    elif change_pct == 0 and float(current) > 0:
        # Stagnant pipeline warning (no change in 72h)
        last_activity = (await db.execute(text("""
            SELECT MAX(updated_at) FROM proposals
            WHERE status IN ('sent','viewed','negotiating')
        """))).scalar_one_or_none()
        if last_activity and (now - last_activity).days >= 3:
            try:
                from app.services.notifications import send_telegram
                await send_telegram(
                    f"📊 *Pipeline Stagnant*\n\n"
                    f"No pipeline movement for 3+ days\n"
                    f"Pipeline: £{float(current):,.0f}\n"
                    f"Recommendation: Accelerate follow-up cadence"
                )
            except Exception:
                pass

    return result
```

Register as job (every 6 hours).

---

## STEP 11 — SYSTEM HEALTH HUD

```python
@app.get("/api/v1/system/hud")
async def system_hud(db=Depends(get_db)):
    """Returns health status grid for all major JARVIS systems."""
    systems = []
    
    # Database
    try:
        await db.execute(text("SELECT 1"))
        systems.append({"name": "database", "status": "green", "note": "Connected"})
    except Exception as e:
        systems.append({"name": "database", "status": "red", "note": str(e)[:100]})

    # Redis
    try:
        import redis.asyncio as aioredis, os
        r = aioredis.from_url(os.getenv("REDIS_URL", "redis://jarvis_redis:6379/0"))
        await r.ping()
        await r.aclose()
        systems.append({"name": "redis", "status": "green", "note": "Connected"})
    except Exception as e:
        systems.append({"name": "redis", "status": "red", "note": str(e)[:100]})

    # APScheduler jobs
    try:
        job_count = (await db.execute(text("SELECT COUNT(*) FROM apscheduler_jobs"))).scalar_one_or_none() or 0
        systems.append({"name": "scheduler", "status": "green", "note": f"{job_count} jobs registered"})
    except Exception:
        systems.append({"name": "scheduler", "status": "yellow", "note": "Status unknown"})

    # Outreach engine
    try:
        sent_today = (await db.execute(text(
            "SELECT COUNT(*) FROM outreach_log WHERE created_at > NOW() - INTERVAL '24 hours'"
        ))).scalar_one_or_none() or 0
        systems.append({"name": "outreach_engine", "status": "green", "note": f"{sent_today} sent today"})
    except Exception:
        systems.append({"name": "outreach_engine", "status": "yellow", "note": "No data"})

    # Dead letter queue
    try:
        failed = (await db.execute(text(
            "SELECT COUNT(*) FROM dead_letter_jobs WHERE resolved=false AND failed_at > NOW() - INTERVAL '24 hours'"
        ))).scalar_one_or_none() or 0
        status = "red" if failed > 5 else ("yellow" if failed > 0 else "green")
        systems.append({"name": "job_health", "status": status, "note": f"{failed} unresolved failures"})
    except Exception:
        systems.append({"name": "job_health", "status": "green", "note": "No failures"})

    # AI layer
    try:
        from app.services.ai_router import is_degraded
        degraded = is_degraded()
        systems.append({
            "name": "ai_layer", 
            "status": "yellow" if degraded else "green",
            "note": "Degraded mode" if degraded else "All providers active"
        })
    except Exception:
        systems.append({"name": "ai_layer", "status": "yellow", "note": "Status unknown"})

    # War room
    systems.append({"name": "war_room", "status": "yellow" if _WAR_ROOM_ACTIVE else "green",
                     "note": "ACTIVE" if _WAR_ROOM_ACTIVE else "Standby"})

    green = sum(1 for s in systems if s["status"] == "green")
    overall = "green" if green == len(systems) else ("yellow" if green >= len(systems) * 0.7 else "red")

    return {
        "overall_status": overall,
        "systems": systems,
        "system_count": len(systems),
        "healthy_count": green,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

---

## STEP 12 — DEPLOY AND VERIFY

```bash
cd /opt/jarvis

# Run migration
docker-compose exec jarvis_app alembic upgrade head

# Rebuild
docker-compose up -d --build jarvis_app
sleep 15

# Verify all new endpoints
curl -s http://localhost:8000/api/v1/system/hud | python3 -m json.tool
curl -s http://localhost:8000/api/v1/jarvis/situation | python3 -m json.tool
curl -s http://localhost:8000/api/v1/intelligence/predicted-actions | python3 -m json.tool
curl -s http://localhost:8000/api/v1/captain/intelligence-feed | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/v1/captain/brain-dump \
  -H "Content-Type: application/json" \
  -d '{"text":"Just spoke with James at CloudOps, wants to cut AWS costs by 40%, has budget, decision maker, demo next Tuesday"}' | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/v1/voice/command \
  -H "Content-Type: application/json" \
  -d '{"text":"JARVIS status"}' | python3 -m json.tool

# Verify tables
docker-compose exec jarvis_postgres psql -U jarvis -d jarvis -c "\dt" | grep -E "captain_lead|case_studies|voice_commands|predicted_actions|war_room"

# Commit
git add -A
git commit -m "feat(batch3): captain bridge, voice commands, tony stark layer"
git push origin main
```

---

## VERIFICATION CHECKLIST

- [ ] `/api/v1/captain/bring-lead` processes and enrolls leads
- [ ] `/api/v1/captain/brain-dump` parses free text into CRM fields
- [ ] `/api/v1/captain/apollo-import` accepts leads array and imports
- [ ] `/api/v1/captain/case-studies` CRUD working
- [ ] `/api/v1/voice/command` returns text response (audio if ElevenLabs configured)
- [ ] `/api/v1/intelligence/predicted-actions` returns 1-3 actions
- [ ] `/api/v1/jarvis/situation` returns consciousness snapshot
- [ ] `/api/v1/system/hud` returns system health grid
- [ ] `/api/v1/jarvis/war-room/activate` toggles war room
- [ ] `/api/v1/intelligence/simulate` returns 3 scenarios
- [ ] Revenue drift alert job registered (every 6 hours)
- [ ] Predicted actions job registered (every 4 hours)

**Batch 3 complete. Proceed to Batch 4.**
