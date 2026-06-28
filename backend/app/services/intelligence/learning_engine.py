"""
JARVIS Learning & Evolution Engine — Every delivery compounding into future advantage.
Client Project → Lessons Learned → SOP Update → Proposal Improvement → Outreach Optimization → Institutional Wisdom.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def _coerce_tenant_id(tenant_id: Any) -> UUID:
    if tenant_id is None:
        return SYSTEM_TENANT_ID
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


class LearningEngine:
    """Converts every delivery into compounding institutional advantage."""

    async def extract_delivery_lessons(
        self,
        tenant_id: Any,
        project_type: str,
        client_industry: str | None,
        delivery_data: dict,
    ) -> dict:
        from app.models.truth_resilience import DeliveryLesson, ImprovementRecommendation
        tid = _coerce_tenant_id(tenant_id)

        what_worked = delivery_data.get("what_worked", "")
        what_failed = delivery_data.get("what_failed", "")
        estimated_days = delivery_data.get("estimated_days")
        actual_days = delivery_data.get("actual_days")
        client_feedback = delivery_data.get("client_feedback", "")
        service_category = delivery_data.get("service_category", project_type)

        effort_accuracy_pct = None
        if estimated_days and actual_days and estimated_days > 0:
            effort_accuracy_pct = max(0.0, (1 - abs(estimated_days - actual_days) / estimated_days) * 100)

        ai_lessons = await self._ai_extract_lessons(project_type, delivery_data)

        lessons_created = 0
        recommendations_created = 0

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)

            for lesson_data in ai_lessons:
                lesson = DeliveryLesson(
                    tenant_id=tid,
                    project_type=project_type,
                    client_industry=client_industry,
                    lesson_category=lesson_data.get("category", "technical"),
                    lesson_title=lesson_data.get("title", "Delivery Lesson"),
                    lesson_body=lesson_data.get("body", ""),
                    what_worked=what_worked,
                    what_failed=what_failed,
                    do_next_time=lesson_data.get("do_next_time", ""),
                    estimated_effort_days=estimated_days,
                    actual_effort_days=actual_days,
                    effort_accuracy_pct=effort_accuracy_pct,
                    tags=lesson_data.get("tags", []),
                )
                db.add(lesson)
                lessons_created += 1

            # Auto-generate improvement recommendations
            if what_failed:
                rec = ImprovementRecommendation(
                    tenant_id=tid,
                    recommendation_type="delivery",
                    source_type="delivery_lesson",
                    title=f"Delivery improvement for {project_type}",
                    description=f"Based on delivery of {project_type}: {what_failed[:400]}",
                    priority="high" if effort_accuracy_pct is not None and effort_accuracy_pct < 60 else "medium",
                    estimated_impact=f"Improve delivery accuracy from {effort_accuracy_pct:.0f}% to >85%" if effort_accuracy_pct else "Reduce delivery failures",
                )
                db.add(rec)
                recommendations_created += 1

            if estimated_days and actual_days and actual_days > estimated_days * 1.25:
                sop_rec = ImprovementRecommendation(
                    tenant_id=tid,
                    recommendation_type="sop",
                    source_type="delivery_lesson",
                    title=f"SOP update: {project_type} estimation accuracy",
                    description=f"Project ran {((actual_days - estimated_days) / estimated_days * 100):.0f}% over estimate. Update scoping SOP to include buffer for {service_category} projects.",
                    priority="high",
                    estimated_impact="Reduce estimation overruns by 30%+",
                )
                db.add(sop_rec)
                recommendations_created += 1

            if client_feedback:
                proposal_rec = ImprovementRecommendation(
                    tenant_id=tid,
                    recommendation_type="proposal",
                    source_type="delivery_lesson",
                    title=f"Proposal optimization: {project_type} client alignment",
                    description=f"Client feedback from {project_type} delivery: {client_feedback[:400]}",
                    priority="medium",
                    estimated_impact="Improve proposal-to-close rate by 10-15%",
                )
                db.add(proposal_rec)
                recommendations_created += 1

            await db.commit()

        return {
            "lessons_created": lessons_created,
            "recommendations_created": recommendations_created,
            "effort_accuracy_pct": effort_accuracy_pct,
            "project_type": project_type,
        }

    async def _ai_extract_lessons(self, project_type: str, delivery_data: dict) -> list[dict]:
        """Use AI to extract structured lessons. Falls back to rule-based extraction."""
        try:
            from app.services.ai.router import ai_router, TaskType
            prompt = f"""Extract structured delivery lessons from this project data.
Project Type: {project_type}
What Worked: {delivery_data.get('what_worked', 'N/A')}
What Failed: {delivery_data.get('what_failed', 'N/A')}
Client Feedback: {delivery_data.get('client_feedback', 'N/A')}

Return 2-3 specific, actionable lessons in JSON array format:
[{{"title": "...", "body": "...", "category": "technical|communication|scoping|timeline|pricing|client_management", "do_next_time": "...", "tags": ["..."]}}]

Return only valid JSON."""
            from app.services.ai.base_provider import Message
            response, _ = await asyncio.wait_for(
                ai_router.chat(
                    [Message(role="user", content=prompt)],
                    task_type=TaskType.ANALYSIS,
                    max_tokens=800,
                ),
                timeout=30.0,
            )
            import json
            content = response.content or "[]"
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except Exception as exc:
            logger.debug("AI lesson extraction failed, using rule-based: %s", exc)

        # Rule-based fallback
        lessons = []
        if delivery_data.get("what_worked"):
            lessons.append({
                "title": f"Successful approach in {project_type}",
                "body": delivery_data["what_worked"],
                "category": "technical",
                "do_next_time": "Replicate this approach in similar projects",
                "tags": [project_type],
            })
        if delivery_data.get("what_failed"):
            lessons.append({
                "title": f"Failure mode in {project_type}",
                "body": delivery_data["what_failed"],
                "category": "scoping",
                "do_next_time": "Avoid this approach. Build mitigation into scoping.",
                "tags": [project_type, "avoid"],
            })
        return lessons

    async def generate_sop_recommendation(self, tenant_id: Any, lesson_ids: list) -> dict:
        from app.models.truth_resilience import DeliveryLesson, ImprovementRecommendation
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(DeliveryLesson).where(
                    DeliveryLesson.tenant_id == tid,
                    DeliveryLesson.id.in_(lesson_ids),
                )
            )
            lessons = result.scalars().all()
            if not lessons:
                return {"error": "no lessons found"}

            combined = "\n".join(f"- {l.lesson_title}: {l.lesson_body}" for l in lessons)
            rec = ImprovementRecommendation(
                tenant_id=tid,
                recommendation_type="sop",
                source_type="delivery_lesson",
                title=f"SOP Update from {len(lessons)} delivery lessons",
                description=f"Aggregate SOP recommendation from analyzed lessons:\n{combined[:1000]}",
                priority="high",
                estimated_impact="Standardize delivery process and reduce variance",
            )
            db.add(rec)
            await db.commit()
            return {"recommendation_type": "sop", "title": rec.title, "description": rec.description}

    async def generate_proposal_optimization(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import DeliveryLesson, ImprovementRecommendation
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(DeliveryLesson).where(
                    DeliveryLesson.tenant_id == tid,
                    DeliveryLesson.effort_accuracy_pct < 80,
                ).order_by(DeliveryLesson.created_at.desc()).limit(10)
            )
            lessons = result.scalars().all()
            description = "Proposal optimization based on delivery accuracy analysis. "
            if lessons:
                avg_acc = sum(l.effort_accuracy_pct or 0 for l in lessons) / len(lessons)
                description += f"Average effort accuracy: {avg_acc:.1f}%. "
                description += "Recommend adding 25% buffer to all time estimates and including explicit scope boundary language in proposals."
            else:
                description += "Insufficient delivery data. Complete first 3 projects before optimizing."

            rec = ImprovementRecommendation(
                tenant_id=tid,
                recommendation_type="proposal",
                source_type="performance_data",
                title="Proposal Optimization — Delivery Accuracy Analysis",
                description=description,
                priority="medium",
                estimated_impact="Improve proposal accuracy and reduce scope creep disputes",
            )
            db.add(rec)
            await db.commit()
            return {"recommendation_type": "proposal", "title": rec.title, "description": rec.description}

    async def generate_outreach_optimization(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import ImprovementRecommendation
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            try:
                from app.models.outreach import OutreachEmail
                from sqlalchemy import select, func
                result = await db.execute(
                    select(
                        func.count().label("total"),
                        func.count(OutreachEmail.reply_received.is_(True)).label("replied"),
                    ).where(OutreachEmail.tenant_id == tid)
                )
                row = result.first()
                total = row.total if row else 0
                replied = row.replied if row else 0
                reply_rate = (replied / total * 100) if total > 0 else 0
                description = f"Outreach optimization analysis. Total sent: {total}. Reply rate: {reply_rate:.1f}%. "
                if reply_rate < 3:
                    description += "Reply rate below 3% threshold. Recommend: stronger personalization hooks, shorter email body, clearer CTA, test different send times."
                elif reply_rate < 8:
                    description += "Reply rate moderate. Recommend: A/B test subject lines, add industry-specific pain points."
                else:
                    description += "Strong reply rate. Scale current outreach approach. Increase volume to DAILY_CAP safely."
            except Exception:
                description = "Outreach performance data not yet available. Begin outreach campaigns to generate optimization data."

            rec = ImprovementRecommendation(
                tenant_id=tid,
                recommendation_type="outreach",
                source_type="performance_data",
                title="Outreach Optimization — Reply Rate Analysis",
                description=description,
                priority="high",
                estimated_impact="Improve reply rate → more demos → more revenue",
            )
            db.add(rec)
            await db.commit()
            return {"recommendation_type": "outreach", "title": rec.title, "description": rec.description}

    async def apply_recommendation(
        self, tenant_id: Any, recommendation_id: int, applied_by: str = "JARVIS"
    ) -> dict:
        from app.models.truth_resilience import ImprovementRecommendation
        from sqlalchemy import select
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(ImprovementRecommendation).where(
                    ImprovementRecommendation.id == recommendation_id,
                    ImprovementRecommendation.tenant_id == tid,
                )
            )
            rec = result.scalar_one_or_none()
            if not rec:
                return {"error": "recommendation not found"}
            rec.implementation_status = "applied"
            rec.applied_at = datetime.now(timezone.utc)
            rec.applied_by = applied_by
            await db.commit()
            return {"status": "applied", "recommendation_id": recommendation_id}

    async def get_learning_dashboard(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import DeliveryLesson, ImprovementRecommendation
        from sqlalchemy import select, func
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)

            lessons_count = (await db.execute(
                select(func.count()).select_from(DeliveryLesson).where(DeliveryLesson.tenant_id == tid)
            )).scalar() or 0

            pending = (await db.execute(
                select(func.count()).select_from(ImprovementRecommendation).where(
                    ImprovementRecommendation.tenant_id == tid,
                    ImprovementRecommendation.implementation_status == "pending",
                )
            )).scalar() or 0

            applied = (await db.execute(
                select(func.count()).select_from(ImprovementRecommendation).where(
                    ImprovementRecommendation.tenant_id == tid,
                    ImprovementRecommendation.implementation_status == "applied",
                )
            )).scalar() or 0

            avg_acc_result = await db.execute(
                select(func.avg(DeliveryLesson.effort_accuracy_pct)).where(
                    DeliveryLesson.tenant_id == tid,
                    DeliveryLesson.effort_accuracy_pct.isnot(None),
                )
            )
            avg_effort_accuracy = avg_acc_result.scalar()

            recent_lessons = await db.execute(
                select(DeliveryLesson).where(DeliveryLesson.tenant_id == tid).order_by(DeliveryLesson.created_at.desc()).limit(5)
            )

        return {
            "lessons_count": lessons_count,
            "pending_recommendations": pending,
            "applied_recommendations": applied,
            "avg_effort_accuracy": round(avg_effort_accuracy, 2) if avg_effort_accuracy else None,
            "evolution_score": min(100, lessons_count * 10 + applied * 5),
            "recent_lessons": [
                {
                    "project_type": l.project_type,
                    "lesson_title": l.lesson_title,
                    "lesson_category": l.lesson_category,
                    "effort_accuracy_pct": l.effort_accuracy_pct,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in recent_lessons.scalars().all()
            ],
        }


learning_engine = LearningEngine()
