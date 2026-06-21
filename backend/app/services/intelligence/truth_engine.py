"""
JARVIS Truth Engine — Prediction vs Reality scoring system.
Continuously compares all AI/council/DIO predictions against actual business outcomes.
Calibrates model weights. Reports accuracy trends to Captain.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, set_tenant_context

logger = logging.getLogger(__name__)

SYSTEM_TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

PREDICTION_TYPES = [
    "lead_score",
    "trust_score",
    "proposal_acceptance",
    "revenue_forecast",
    "client_health",
    "council_recommendation",
    "dio_recommendation",
    "delivery_estimate",
]


def _coerce_tenant_id(tenant_id: Any) -> UUID:
    if tenant_id is None:
        return SYSTEM_TENANT_ID
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


class TruthEngine:
    """Tracks every prediction made by JARVIS and scores accuracy against reality."""

    async def record_prediction(
        self,
        tenant_id: Any,
        prediction_type: str,
        entity_type: str,
        entity_id: str | None = None,
        predicted_value: float | None = None,
        predicted_label: str | None = None,
        predicted_by: str = "jarvis",
        confidence_score: float | None = None,
        metadata: dict | None = None,
    ) -> dict:
        from app.models.truth_resilience import TruthEvent
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            row = TruthEvent(
                tenant_id=tid,
                prediction_type=prediction_type,
                entity_type=entity_type,
                entity_id=entity_id,
                predicted_value=predicted_value,
                predicted_label=predicted_label,
                predicted_by=predicted_by,
                confidence_score=confidence_score,
                metadata_json=metadata or {},
                outcome_recorded=False,
            )
            db.add(row)
            await db.flush()
            row_id = row.id
            await db.commit()
        logger.debug("Truth prediction recorded id=%s type=%s", row_id, prediction_type)
        return {"id": row_id, "status": "recorded", "prediction_type": prediction_type}

    async def record_outcome(
        self,
        tenant_id: Any,
        truth_event_id: int,
        outcome_value: float | None = None,
        outcome_label: str | None = None,
    ) -> dict:
        from app.models.truth_resilience import TruthEvent
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(TruthEvent).where(
                    TruthEvent.id == truth_event_id,
                    TruthEvent.tenant_id == tid,
                )
            )
            row = result.scalar_one_or_none()
            if not row:
                return {"error": "truth_event not found"}

            accuracy_delta = None
            if row.predicted_value is not None and outcome_value is not None:
                accuracy_delta = abs(row.predicted_value - outcome_value)

            row.outcome_value = outcome_value
            row.outcome_label = outcome_label
            row.outcome_recorded = True
            row.accuracy_delta = accuracy_delta
            row.outcome_recorded_at = datetime.now(timezone.utc)
            await db.commit()

            # Recompute accuracy stats for this prediction type
            await self._recompute_accuracy(db, tid, row.prediction_type)

        return {
            "id": truth_event_id,
            "accuracy_delta": accuracy_delta,
            "status": "recorded",
        }

    async def _recompute_accuracy(
        self, db: AsyncSession, tenant_id: UUID, prediction_type: str
    ) -> None:
        from app.models.truth_resilience import TruthEvent, PredictionAccuracy
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = await db.execute(
            select(TruthEvent).where(
                TruthEvent.tenant_id == tenant_id,
                TruthEvent.prediction_type == prediction_type,
                TruthEvent.outcome_recorded == True,
                TruthEvent.created_at >= cutoff,
            )
        )
        events = result.scalars().all()

        if not events:
            return

        deltas = [e.accuracy_delta for e in events if e.accuracy_delta is not None]
        total = len(events)
        scored = len(deltas)

        mae = sum(deltas) / len(deltas) if deltas else None
        accuracy_score = max(0.0, 100.0 - (mae * 100)) if mae is not None else None

        # Calibration: pct where delta < 20% of predicted value
        calibrated = 0
        for e in events:
            if e.accuracy_delta is not None and e.predicted_value and e.predicted_value != 0:
                if abs(e.accuracy_delta / e.predicted_value) < 0.20:
                    calibrated += 1
        calibration_score = calibrated / scored if scored > 0 else None

        # Trend: compare accuracy this week vs last week
        one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        two_weeks_ago = datetime.now(timezone.utc) - timedelta(days=14)
        this_week = [e for e in events if e.created_at and e.created_at >= one_week_ago]
        last_week = [e for e in events if e.created_at and two_weeks_ago <= e.created_at < one_week_ago]

        trend = "stable"
        if this_week and last_week:
            tw_deltas = [e.accuracy_delta for e in this_week if e.accuracy_delta is not None]
            lw_deltas = [e.accuracy_delta for e in last_week if e.accuracy_delta is not None]
            if tw_deltas and lw_deltas:
                tw_mae = sum(tw_deltas) / len(tw_deltas)
                lw_mae = sum(lw_deltas) / len(lw_deltas)
                if tw_mae < lw_mae * 0.9:
                    trend = "improving"
                elif tw_mae > lw_mae * 1.1:
                    trend = "degrading"

        weight_adjustment = 1.0
        if trend == "improving":
            weight_adjustment = min(1.5, 1.0 + (lw_mae - tw_mae) / max(lw_mae, 0.001))
        elif trend == "degrading":
            weight_adjustment = max(0.5, 1.0 - 0.1)

        period_date = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        existing = await db.execute(
            select(PredictionAccuracy).where(
                PredictionAccuracy.tenant_id == tenant_id,
                PredictionAccuracy.prediction_type == prediction_type,
                PredictionAccuracy.period_date == period_date,
            )
        )
        pa = existing.scalar_one_or_none()
        if pa:
            pa.total_predictions = total
            pa.scored_predictions = scored
            pa.mean_absolute_error = mae
            pa.accuracy_score = accuracy_score
            pa.calibration_score = calibration_score
            pa.trend = trend
            pa.weight_adjustment = weight_adjustment
        else:
            pa = PredictionAccuracy(
                tenant_id=tenant_id,
                prediction_type=prediction_type,
                period_date=period_date,
                total_predictions=total,
                scored_predictions=scored,
                mean_absolute_error=mae,
                accuracy_score=accuracy_score,
                calibration_score=calibration_score,
                trend=trend,
                weight_adjustment=weight_adjustment,
            )
            db.add(pa)
        await db.commit()

    async def run_reality_check(self, tenant_id: Any, check_type: str) -> dict:
        from app.models.truth_resilience import TruthEvent, RealityCheck
        tid = _coerce_tenant_id(tenant_id)
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=30)

        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(TruthEvent).where(
                    TruthEvent.tenant_id == tid,
                    TruthEvent.prediction_type == check_type,
                    TruthEvent.outcome_recorded == True,
                    TruthEvent.created_at >= period_start,
                )
            )
            events = result.scalars().all()

            predicted_vals = [e.predicted_value for e in events if e.predicted_value is not None]
            actual_vals = [e.outcome_value for e in events if e.outcome_value is not None]
            deltas = [e.accuracy_delta for e in events if e.accuracy_delta is not None]

            accuracy_pct = None
            if deltas and predicted_vals:
                mae = sum(deltas) / len(deltas)
                avg_pred = sum(predicted_vals) / len(predicted_vals)
                accuracy_pct = max(0.0, 100.0 - (mae / max(avg_pred, 0.001) * 100))

            gap_analysis = f"Checked {len(events)} predictions of type '{check_type}' over last 30 days. "
            if accuracy_pct is not None:
                gap_analysis += f"Accuracy: {accuracy_pct:.1f}%. "
                if accuracy_pct < 60:
                    gap_analysis += "Model is significantly miscalibrated — consider adjusting scoring weights. "
                elif accuracy_pct < 80:
                    gap_analysis += "Moderate calibration gap — monitor and review scoring logic. "
                else:
                    gap_analysis += "Model is well-calibrated. Continue monitoring. "
            else:
                gap_analysis += "Insufficient data for gap analysis."

            corrective_actions = []
            if accuracy_pct is not None and accuracy_pct < 60:
                corrective_actions.append(f"Reduce confidence weight for {check_type} predictions by 20%")
                corrective_actions.append(f"Schedule manual review of {check_type} scoring logic")

            rc = RealityCheck(
                tenant_id=tid,
                check_type=check_type,
                prediction_summary={"count": len(events), "avg_predicted": sum(predicted_vals) / len(predicted_vals) if predicted_vals else 0},
                reality_summary={"count": len(actual_vals), "avg_actual": sum(actual_vals) / len(actual_vals) if actual_vals else 0},
                accuracy_pct=accuracy_pct,
                gap_analysis=gap_analysis,
                auto_corrective_actions=corrective_actions,
                captain_report_sent=False,
                period_start=period_start,
                period_end=period_end,
            )
            db.add(rc)
            await db.commit()

            return {
                "check_type": check_type,
                "accuracy_pct": accuracy_pct,
                "gap_analysis": gap_analysis,
                "corrective_actions": corrective_actions,
                "events_analyzed": len(events),
            }

    async def get_truth_report(self, tenant_id: Any) -> dict:
        from app.models.truth_resilience import PredictionAccuracy, RealityCheck
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            pa_result = await db.execute(
                select(PredictionAccuracy).where(PredictionAccuracy.tenant_id == tid).order_by(PredictionAccuracy.period_date.desc()).limit(50)
            )
            accuracies = pa_result.scalars().all()

            rc_result = await db.execute(
                select(RealityCheck).where(RealityCheck.tenant_id == tid).order_by(RealityCheck.created_at.desc()).limit(10)
            )
            reality_checks = rc_result.scalars().all()

            scores = [a.accuracy_score for a in accuracies if a.accuracy_score is not None]
            overall_calibration = sum(scores) / len(scores) if scores else 0.0

            accuracy_by_type = [
                {
                    "prediction_type": a.prediction_type,
                    "accuracy_score": a.accuracy_score,
                    "trend": a.trend,
                    "total_predictions": a.total_predictions,
                    "scored_predictions": a.scored_predictions,
                    "mean_absolute_error": a.mean_absolute_error,
                    "calibration_score": a.calibration_score,
                    "weight_adjustment": a.weight_adjustment,
                    "period_date": a.period_date.isoformat() if a.period_date else None,
                }
                for a in accuracies
            ]

            sorted_by_accuracy = sorted(
                [a for a in accuracy_by_type if a["accuracy_score"] is not None],
                key=lambda x: x["accuracy_score"]
            )
            top_failures = sorted_by_accuracy[:3]

            recommendations = []
            for f in top_failures:
                if f["accuracy_score"] is not None and f["accuracy_score"] < 60:
                    recommendations.append(f"CRITICAL: {f['prediction_type']} accuracy at {f['accuracy_score']:.1f}% — review scoring model immediately")
                elif f["accuracy_score"] is not None and f["accuracy_score"] < 80:
                    recommendations.append(f"Monitor {f['prediction_type']} accuracy ({f['accuracy_score']:.1f}%) — trending {f.get('trend','unknown')}")

            return {
                "overall_calibration_score": round(overall_calibration, 2),
                "accuracy_by_type": accuracy_by_type,
                "recent_reality_checks": [
                    {
                        "check_type": rc.check_type,
                        "accuracy_pct": rc.accuracy_pct,
                        "gap_analysis": rc.gap_analysis,
                        "corrective_actions": rc.auto_corrective_actions,
                        "period_start": rc.period_start.isoformat() if rc.period_start else None,
                        "period_end": rc.period_end.isoformat() if rc.period_end else None,
                        "created_at": rc.created_at.isoformat() if rc.created_at else None,
                    }
                    for rc in reality_checks
                ],
                "top_failures": top_failures,
                "recommendations": recommendations,
            }

    async def get_accuracy_dashboard(self, tenant_id: Any) -> list:
        from app.models.truth_resilience import PredictionAccuracy
        tid = _coerce_tenant_id(tenant_id)
        async with AsyncSessionLocal() as db:
            await set_tenant_context(db, tid)
            result = await db.execute(
                select(PredictionAccuracy).where(PredictionAccuracy.tenant_id == tid).order_by(PredictionAccuracy.accuracy_score.asc().nulls_last())
            )
            rows = result.scalars().all()
            return [
                {
                    "prediction_type": r.prediction_type,
                    "accuracy_score": r.accuracy_score,
                    "trend": r.trend,
                    "total_predictions": r.total_predictions,
                    "mean_absolute_error": r.mean_absolute_error,
                    "weight_adjustment": r.weight_adjustment,
                }
                for r in rows
            ]


truth_engine = TruthEngine()
