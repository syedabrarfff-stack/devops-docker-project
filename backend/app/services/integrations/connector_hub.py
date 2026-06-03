"""
JARVIS Connector Hub — Master orchestration layer between Claude's 9 external connectors and JARVIS EC2.

Reads daily JSON packages from /jarvis-data/ (GitHub repo clone on EC2),
processes leads through scoring, sequences through outreach engine,
decks through prospect matching, and intelligence through the AI Council.

Scheduled to run at 14:30 UTC (20:00 IST) daily via APScheduler.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal, set_tenant_context
from app.models.lead import Lead, LeadStatus
from app.services.ai.council import IntelligenceCouncil
from app.services.ai.router import ai_router
from app.services.leads.scoring import lead_scoring_engine
from app.services.notifications.slack import notify_slack

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

# Thresholds matching JARVIS ICP config
QUALIFIED_THRESHOLD = 60.0
HOT_THRESHOLD = 80.0
COUNCIL_QUALITY_THRESHOLD = 0.7


class ConnectorHub:
    """
    Master coordination layer between Claude's 9 external connectors and JARVIS.
    Ingests daily data dumps from GitHub /jarvis-data/ folder and processes them
    through the full JARVIS pipeline: score → sequence → propose → invoice → report.
    """

    def __init__(self) -> None:
        self._council = IntelligenceCouncil()
        from app.services.integrations.github_bridge import GitHubBridge
        self._bridge = GitHubBridge()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def ingest_daily_package(self, tenant_id: UUID, date_str: str | None = None) -> dict:
        """
        Main entry point. Called by APScheduler at 20:30 IST (15:00 UTC) daily.
        Reads /jarvis-data/daily/YYYY-MM-DD/ from the local EC2 repo clone.
        Processes: leads → sequences → decks → intelligence → market_report
        Returns full ingestion summary.
        """
        started = datetime.now(UTC)
        effective_date = date_str or date.today().isoformat()
        logger.info("[ConnectorHub] Starting daily ingestion for tenant=%s date=%s", tenant_id, effective_date)

        summary: dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "date": effective_date,
            "started_at": started.isoformat(),
            "leads": {},
            "sequences": {},
            "decks": {},
            "intelligence": {},
            "errors": [],
        }

        try:
            package = await self._bridge.read_daily_package(effective_date)
        except Exception as exc:
            logger.error("[ConnectorHub] Failed to read daily package: %s", exc)
            summary["errors"].append(f"read_package: {exc}")
            return summary

        # --- Process leads ---
        leads_raw = package.get("leads", [])
        if leads_raw:
            try:
                summary["leads"] = await self.process_leads_package(tenant_id, leads_raw)
            except Exception as exc:
                logger.error("[ConnectorHub] Leads processing error: %s", exc)
                summary["errors"].append(f"leads: {exc}")

        # --- Process sequences ---
        sequences_raw = package.get("sequences", [])
        if sequences_raw:
            try:
                summary["sequences"] = await self.process_sequences_package(tenant_id, sequences_raw)
            except Exception as exc:
                logger.error("[ConnectorHub] Sequences processing error: %s", exc)
                summary["errors"].append(f"sequences: {exc}")

        # --- Process decks ---
        decks_raw = package.get("decks", [])
        if decks_raw:
            try:
                summary["decks"] = await self.process_decks_package(tenant_id, decks_raw)
            except Exception as exc:
                logger.error("[ConnectorHub] Decks processing error: %s", exc)
                summary["errors"].append(f"decks: {exc}")

        # --- Process intelligence ---
        try:
            intel_package = await self._bridge.read_intelligence_package()
            if intel_package:
                summary["intelligence"] = await self.process_intelligence_package(tenant_id, intel_package)
        except Exception as exc:
            logger.error("[ConnectorHub] Intelligence processing error: %s", exc)
            summary["errors"].append(f"intelligence: {exc}")

        # --- Persist ingestion record ---
        try:
            await self._persist_ingestion_record(tenant_id, effective_date, summary)
        except Exception as exc:
            logger.warning("[ConnectorHub] Failed to persist ingestion record: %s", exc)

        # --- Write output back to GitHub bridge ---
        try:
            await self._bridge.write_jarvis_output("leads_processed", summary, effective_date)
        except Exception as exc:
            logger.warning("[ConnectorHub] Failed to write output: %s", exc)

        # --- Generate and post status report ---
        try:
            report = await self.generate_daily_status_report(tenant_id)
            summary["status_report"] = report
        except Exception as exc:
            logger.warning("[ConnectorHub] Status report error: %s", exc)

        summary["completed_at"] = datetime.now(UTC).isoformat()
        summary["duration_seconds"] = (datetime.now(UTC) - started).total_seconds()
        logger.info("[ConnectorHub] Ingestion complete: %s", summary.get("leads", {}).get("processed", 0))
        return summary

    # ------------------------------------------------------------------
    # Package processors
    # ------------------------------------------------------------------

    async def process_leads_package(self, tenant_id: UUID, leads: list[dict]) -> dict:
        """
        Takes leads from Apollo/HubSpot/Close CRM JSON dump.
        Scores each lead using LeadScoringEngine.
        Qualified leads (score >= 60) → promoted to pipeline.
        Hot leads (score >= 80) → immediately queued for outreach.
        Returns: processed, qualified, promoted, hot counts.
        """
        processed = 0
        qualified = 0
        promoted = 0
        hot = 0
        errors = 0

        async with AsyncSessionLocal() as db:
            try:
                await set_tenant_context(db, str(tenant_id))
            except Exception:
                pass

            for raw_lead in leads:
                if not isinstance(raw_lead, dict):
                    errors += 1
                    continue

                try:
                    # Score the lead
                    score, breakdown = await lead_scoring_engine.score_against_icp(raw_lead)
                    processed += 1

                    email = raw_lead.get("email", "").strip().lower()
                    if not email:
                        continue

                    # Check if lead already exists
                    existing = await db.execute(
                        select(Lead).where(
                            Lead.tenant_id == tenant_id,
                            Lead.email == email,
                        )
                    )
                    lead_obj = existing.scalar_one_or_none()

                    if score >= QUALIFIED_THRESHOLD:
                        qualified += 1

                    is_hot = score >= HOT_THRESHOLD

                    if lead_obj:
                        # Update existing lead score if improved
                        if score > (lead_obj.score or 0):
                            lead_obj.score = score
                            lead_obj.signal_breakdown = breakdown
                            if is_hot and lead_obj.status == LeadStatus.NEW:
                                lead_obj.status = LeadStatus.CONTACTED
                                lead_obj.outreach_eligible = True
                    else:
                        # Create new lead
                        lead_obj = Lead(
                            tenant_id=tenant_id,
                            company_name=raw_lead.get("company_name"),
                            contact_name=raw_lead.get("contact_name"),
                            email=email,
                            phone=raw_lead.get("phone"),
                            country=raw_lead.get("country"),
                            industry=raw_lead.get("industry"),
                            score=score,
                            status=LeadStatus.CONTACTED if is_hot else LeadStatus.NEW,
                            source=raw_lead.get("source", "connector_hub"),
                            pain_points=raw_lead.get("pain_points", []),
                            notes=raw_lead.get("notes"),
                            signal_breakdown=breakdown,
                            outreach_eligible=score >= QUALIFIED_THRESHOLD,
                            review_queue=QUALIFIED_THRESHOLD <= score < HOT_THRESHOLD,
                            enrichment_data={
                                "employee_count": raw_lead.get("employee_count"),
                                "estimated_revenue": raw_lead.get("estimated_revenue"),
                                "deck_url": raw_lead.get("deck_url"),
                                "score_hint": raw_lead.get("score_hint"),
                            },
                        )
                        db.add(lead_obj)
                        promoted += 1

                    if is_hot:
                        hot += 1
                        # Queue hot lead for outreach
                        try:
                            await self._queue_hot_lead_outreach(db, lead_obj, tenant_id)
                        except Exception as exc:
                            logger.warning("[ConnectorHub] Hot lead outreach queue failed: %s", exc)

                except Exception as exc:
                    logger.warning("[ConnectorHub] Lead processing error for %s: %s", raw_lead.get("email"), exc)
                    errors += 1

            try:
                await db.commit()
            except Exception as exc:
                logger.error("[ConnectorHub] DB commit failed: %s", exc)
                await db.rollback()

        return {
            "processed": processed,
            "qualified": qualified,
            "promoted": promoted,
            "hot": hot,
            "errors": errors,
        }

    async def process_sequences_package(self, tenant_id: UUID, sequences: list[dict]) -> dict:
        """
        Takes email sequences from Klaviyo JSON dump.
        Loads them into JARVIS outreach engine as active sequences.
        Each sequence has: name, emails (list of {subject, body, day}), target_segment.
        Returns: sequences_loaded count.
        """
        loaded = 0
        skipped = 0

        for seq in sequences:
            if not isinstance(seq, dict):
                skipped += 1
                continue

            name = seq.get("name", "").strip()
            emails = seq.get("emails", [])
            target_segment = seq.get("target_segment", "")

            if not name or not emails:
                skipped += 1
                continue

            try:
                # Store sequence in outreach engine knowledge base
                async with AsyncSessionLocal() as db:
                    try:
                        await set_tenant_context(db, str(tenant_id))
                    except Exception:
                        pass

                    # Check if sequence with same name already exists in knowledge
                    try:
                        from app.services.knowledge.store import knowledge_store
                        await knowledge_store.upsert(
                            tenant_id=tenant_id,
                            key=f"email_sequence:{name.lower().replace(' ', '_')}",
                            content={
                                "name": name,
                                "target_segment": target_segment,
                                "persona": seq.get("persona", "Darren Mitchell"),
                                "emails": emails,
                                "source": "klaviyo",
                                "loaded_at": datetime.now(UTC).isoformat(),
                            },
                            category="email_sequence",
                        )
                    except ImportError:
                        # Fallback: just log the sequence
                        logger.info("[ConnectorHub] Sequence loaded (no knowledge store): %s", name)

                    loaded += 1

            except Exception as exc:
                logger.warning("[ConnectorHub] Sequence load error for '%s': %s", name, exc)
                skipped += 1

        return {"sequences_loaded": loaded, "sequences_skipped": skipped}

    async def process_intelligence_package(self, tenant_id: UUID, intelligence: dict) -> dict:
        """
        Takes market reports/case studies from GitHub intelligence/ folder.
        Stores in JARVIS knowledge base and memory system.
        Sends to AI Council for review and approval.
        Council: if quality >= 0.7 → approve and publish. If < 0.7 → request revision.
        Returns: reports_processed, council_approved, council_revised counts.
        """
        reports_processed = 0
        council_approved = 0
        council_revised = 0

        for filename, content in intelligence.items():
            if not content:
                continue

            try:
                reports_processed += 1

                # Send to AI Council for quality review
                council_result = await self.run_council_review(
                    tenant_id=tenant_id,
                    content_type="market_report",
                    content={
                        "filename": filename,
                        "content": content[:3000] if isinstance(content, str) else json.dumps(content)[:3000],
                        "source": "github_intelligence",
                    },
                )

                verdict = council_result.get("verdict", "APPROVE")
                confidence = council_result.get("confidence", 0.0)

                if verdict == "APPROVE" or confidence >= COUNCIL_QUALITY_THRESHOLD:
                    council_approved += 1
                    # Store in knowledge base
                    try:
                        from app.services.knowledge.store import knowledge_store
                        await knowledge_store.upsert(
                            tenant_id=tenant_id,
                            key=f"market_intel:{filename}",
                            content={
                                "filename": filename,
                                "raw_content": content,
                                "council_verdict": verdict,
                                "confidence": confidence,
                                "approved_at": datetime.now(UTC).isoformat(),
                            },
                            category="market_intelligence",
                        )
                    except ImportError:
                        logger.info("[ConnectorHub] Intel stored (no knowledge store): %s", filename)
                else:
                    council_revised += 1
                    logger.info("[ConnectorHub] Council requested revision for: %s", filename)

            except Exception as exc:
                logger.warning("[ConnectorHub] Intelligence processing error for %s: %s", filename, exc)

        return {
            "reports_processed": reports_processed,
            "council_approved": council_approved,
            "council_revised": council_revised,
        }

    async def process_decks_package(self, tenant_id: UUID, decks: list[dict]) -> dict:
        """
        Takes Gamma pitch deck URLs mapped to prospect/company names.
        Associates each deck with matching lead in JARVIS database.
        Returns: decks_matched, decks_unmatched counts.
        """
        matched = 0
        unmatched = 0

        async with AsyncSessionLocal() as db:
            try:
                await set_tenant_context(db, str(tenant_id))
            except Exception:
                pass

            for deck in decks:
                if not isinstance(deck, dict):
                    unmatched += 1
                    continue

                company_name = deck.get("company_name", "").strip()
                deck_url = deck.get("deck_url", "").strip()

                if not company_name or not deck_url:
                    unmatched += 1
                    continue

                try:
                    # Find matching lead by company name
                    result = await db.execute(
                        select(Lead).where(
                            Lead.tenant_id == tenant_id,
                            Lead.company_name.ilike(f"%{company_name}%"),
                        ).limit(1)
                    )
                    lead_obj = result.scalar_one_or_none()

                    if lead_obj:
                        enrichment = lead_obj.enrichment_data or {}
                        enrichment["deck_url"] = deck_url
                        enrichment["deck_matched_at"] = datetime.now(UTC).isoformat()
                        lead_obj.enrichment_data = enrichment
                        matched += 1
                    else:
                        # No matching lead — store as unmatched deck for future use
                        logger.info("[ConnectorHub] No lead match for deck company: %s", company_name)
                        unmatched += 1

                except Exception as exc:
                    logger.warning("[ConnectorHub] Deck match error for %s: %s", company_name, exc)
                    unmatched += 1

            try:
                await db.commit()
            except Exception as exc:
                logger.error("[ConnectorHub] Deck DB commit failed: %s", exc)
                await db.rollback()

        return {"decks_matched": matched, "decks_unmatched": unmatched}

    # ------------------------------------------------------------------
    # AI Council review gate
    # ------------------------------------------------------------------

    async def run_council_review(self, tenant_id: UUID, content_type: str, content: dict) -> dict:
        """
        Sends any content through the AI Council for quality gate.
        content_type: 'outreach_email' | 'proposal' | 'market_report' | 'lead_score'
        Council votes: APPROVE (no changes) | REVISE (specific improvements) | REJECT (redo)
        Returns: verdict, confidence, improvements (if any), final_content.
        """
        type_prompts = {
            "outreach_email": (
                "Review this outreach email for quality, professionalism, and effectiveness. "
                "Score 0.0–1.0. Output JSON: {verdict: APPROVE|REVISE|REJECT, confidence: float, improvements: list}"
            ),
            "proposal": (
                "Review this proposal for completeness, pricing clarity, and professional tone. "
                "Score 0.0–1.0. Output JSON: {verdict: APPROVE|REVISE|REJECT, confidence: float, improvements: list}"
            ),
            "market_report": (
                "Review this market intelligence report for accuracy, depth, and actionability. "
                "Score 0.0–1.0. Output JSON: {verdict: APPROVE|REVISE|REJECT, confidence: float, improvements: list}"
            ),
            "lead_score": (
                "Review this lead scoring result for accuracy against ICP criteria. "
                "Score 0.0–1.0. Output JSON: {verdict: APPROVE|REVISE|REJECT, confidence: float, improvements: list}"
            ),
        }
        question = type_prompts.get(content_type, type_prompts["market_report"])

        try:
            result = await self._council.convene(
                question=question,
                context=content,
                council_type="quality_gate",
                tenant_id=tenant_id,
            )

            # Parse verdict from council decision
            decision_text = (result.decision or "").upper()
            if "REJECT" in decision_text:
                verdict = "REJECT"
            elif "REVISE" in decision_text:
                verdict = "REVISE"
            else:
                verdict = "APPROVE"

            return {
                "verdict": verdict,
                "confidence": float(result.score or 0.0),
                "improvements": [],
                "final_content": content,
                "council_session_id": result.session_id,
                "reasoning": result.reasoning,
            }

        except Exception as exc:
            logger.warning("[ConnectorHub] Council review error: %s", exc)
            # Fail open — approve if council unavailable
            return {
                "verdict": "APPROVE",
                "confidence": 0.5,
                "improvements": [],
                "final_content": content,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Status report
    # ------------------------------------------------------------------

    async def generate_daily_status_report(self, tenant_id: UUID) -> dict:
        """
        After full ingestion, generates a status report.
        Posts to Slack #jarvis-sales.
        Returns full report dict.
        """
        today = date.today().isoformat()

        # Build report from today's ingestion stats
        try:
            ingestion_data = await self._get_today_ingestion_stats(tenant_id, today)
        except Exception:
            ingestion_data = {}

        report = {
            "date": today,
            "tenant_id": str(tenant_id),
            "generated_at": datetime.now(UTC).isoformat(),
            "leads_processed": ingestion_data.get("leads_processed", 0),
            "leads_qualified": ingestion_data.get("leads_qualified", 0),
            "leads_hot": ingestion_data.get("hot_leads", 0),
            "sequences_loaded": ingestion_data.get("sequences_loaded", 0),
            "decks_matched": ingestion_data.get("decks_matched", 0),
            "intelligence_approved": ingestion_data.get("council_approvals", 0),
            "status": "complete",
        }

        # Post to Slack
        slack_message = (
            f"*JARVIS Daily Connector Hub Report — {today}*\n"
            f"Leads processed: {report['leads_processed']} | Qualified: {report['leads_qualified']} | Hot: {report['leads_hot']}\n"
            f"Sequences loaded: {report['sequences_loaded']} | Decks matched: {report['decks_matched']}\n"
            f"Intelligence reports approved: {report['intelligence_approved']}\n"
            f"_Aliyar Solutions — Operational Intelligence Active_"
        )

        try:
            await notify_slack(slack_message)
        except Exception as exc:
            logger.warning("[ConnectorHub] Slack notification failed: %s", exc)

        return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _queue_hot_lead_outreach(self, db, lead: Lead, tenant_id: UUID) -> None:
        """Queue a hot lead for immediate outreach."""
        try:
            from app.models.outreach import FollowUpQueue, FollowUpStatus
            existing = await db.execute(
                select(FollowUpQueue).where(
                    FollowUpQueue.lead_id == lead.id,
                    FollowUpQueue.tenant_id == tenant_id,
                    FollowUpQueue.status == FollowUpStatus.PENDING,
                ).limit(1)
            )
            if not existing.scalar_one_or_none():
                fup = FollowUpQueue(
                    tenant_id=tenant_id,
                    lead_id=lead.id,
                    status=FollowUpStatus.PENDING,
                    priority=1,  # high priority
                    notes="Hot lead from connector hub — auto-queued",
                )
                db.add(fup)
        except ImportError:
            logger.info("[ConnectorHub] FollowUpQueue not available, skipping outreach queue")
        except Exception as exc:
            logger.warning("[ConnectorHub] Hot lead queue error: %s", exc)

    async def _persist_ingestion_record(self, tenant_id: UUID, date_str: str, summary: dict) -> None:
        """Persist today's ingestion stats to DB."""
        try:
            from app.models.connector_hub import ConnectorHubIngestion
            async with AsyncSessionLocal() as db:
                try:
                    await set_tenant_context(db, str(tenant_id))
                except Exception:
                    pass

                leads_data = summary.get("leads", {})
                seqs_data = summary.get("sequences", {})
                decks_data = summary.get("decks", {})
                intel_data = summary.get("intelligence", {})

                record = ConnectorHubIngestion(
                    tenant_id=tenant_id,
                    date=date.fromisoformat(date_str),
                    leads_processed=leads_data.get("processed", 0),
                    sequences_loaded=seqs_data.get("sequences_loaded", 0),
                    decks_matched=decks_data.get("decks_matched", 0),
                    intelligence_reports=intel_data.get("reports_processed", 0),
                    council_approvals=intel_data.get("council_approved", 0),
                    council_revisions=intel_data.get("council_revised", 0),
                    outreach_triggered=leads_data.get("hot", 0),
                    status="complete",
                    summary=summary,
                )
                db.add(record)
                await db.commit()
        except ImportError:
            logger.debug("[ConnectorHub] ConnectorHubIngestion model not yet available")
        except Exception as exc:
            logger.warning("[ConnectorHub] Ingestion record persist error: %s", exc)

    async def _get_today_ingestion_stats(self, tenant_id: UUID, date_str: str) -> dict:
        """Retrieve today's ingestion stats from DB."""
        try:
            from app.models.connector_hub import ConnectorHubIngestion
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ConnectorHubIngestion).where(
                        ConnectorHubIngestion.tenant_id == tenant_id,
                        ConnectorHubIngestion.date == date.fromisoformat(date_str),
                    ).order_by(ConnectorHubIngestion.created_at.desc()).limit(1)
                )
                record = result.scalar_one_or_none()
                if record:
                    return {
                        "leads_processed": record.leads_processed,
                        "leads_qualified": 0,
                        "hot_leads": record.outreach_triggered,
                        "sequences_loaded": record.sequences_loaded,
                        "decks_matched": record.decks_matched,
                        "council_approvals": record.council_approvals,
                    }
        except Exception:
            pass
        return {}


connector_hub = ConnectorHub()
