"""AIONX Sovereign Organs — Decision Memory, Counterfactual, Debt, Digital Twins,
Wisdom Index, Provider Council, Grand Convergence Council, Mission Autopsy,
Sentinel Layer, Executive Accountability.

Revision ID: 0017_aionx_sovereign_organs
Revises: 0016_consciousness_upgrade
Create Date: 2026-06-04
"""
from __future__ import annotations

from alembic import op

revision = "0017_aionx_sovereign_organs"
down_revision = "0016_consciousness_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ─── DECISION MEMORY ENGINE ──────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_objects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            client_id UUID,
            mission_id UUID,
            campaign_id UUID,
            tier SMALLINT NOT NULL DEFAULT 2,
            decision_category TEXT NOT NULL DEFAULT 'GENERAL',
            trigger_event TEXT NOT NULL,
            problem_statement TEXT NOT NULL,
            executor_role TEXT NOT NULL DEFAULT 'JARVIS_AUTONOMOUS',
            final_recommendation TEXT,
            confidence_score FLOAT NOT NULL DEFAULT 0.0,
            risk_flags JSONB NOT NULL DEFAULT '[]',
            assumptions JSONB NOT NULL DEFAULT '[]',
            outcome_summary TEXT,
            outcome_at TIMESTAMPTZ,
            pattern_approved_for_reuse BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_options (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_id UUID NOT NULL REFERENCES decision_objects(id) ON DELETE CASCADE,
            option_text TEXT NOT NULL,
            was_chosen BOOLEAN NOT NULL DEFAULT false,
            proponent_brains JSONB NOT NULL DEFAULT '[]',
            opponent_brains JSONB NOT NULL DEFAULT '[]',
            confidence_score FLOAT NOT NULL DEFAULT 0.0,
            predicted_outcome_30d TEXT,
            predicted_outcome_90d TEXT,
            predicted_revenue_impact FLOAT NOT NULL DEFAULT 0.0,
            predicted_reputation_impact FLOAT NOT NULL DEFAULT 0.0,
            opportunity_cost FLOAT NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_outcomes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_id UUID NOT NULL REFERENCES decision_objects(id) ON DELETE CASCADE,
            deployed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            actual_result TEXT,
            day_30_review TEXT,
            day_30_reviewed_at TIMESTAMPTZ,
            day_90_review TEXT,
            day_90_reviewed_at TIMESTAMPTZ,
            confidence_validation TEXT,
            lessons_learned TEXT,
            pattern_approved_for_reuse BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_patterns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern_name TEXT NOT NULL UNIQUE,
            pattern_category TEXT NOT NULL,
            when_to_apply TEXT NOT NULL,
            decision_template JSONB NOT NULL DEFAULT '{}',
            historical_success_rate FLOAT NOT NULL DEFAULT 0.0,
            usage_count INT NOT NULL DEFAULT 0,
            confidence_for_automation FLOAT NOT NULL DEFAULT 0.0,
            last_validated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_retrospectives (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            week_of DATE NOT NULL,
            total_decisions INT NOT NULL DEFAULT 0,
            avg_confidence FLOAT NOT NULL DEFAULT 0.0,
            correct_count INT NOT NULL DEFAULT 0,
            incorrect_count INT NOT NULL DEFAULT 0,
            pattern_insights TEXT,
            council_weight_adjustments JSONB NOT NULL DEFAULT '{}',
            recommended_playbooks JSONB NOT NULL DEFAULT '[]',
            wisdom_delta FLOAT NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── COUNTERFACTUAL ENGINE ───────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS counterfactual_simulations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_id UUID NOT NULL REFERENCES decision_objects(id) ON DELETE CASCADE,
            option_id UUID NOT NULL REFERENCES decision_options(id) ON DELETE CASCADE,
            simulation_narrative TEXT NOT NULL,
            predicted_revenue_impact FLOAT NOT NULL DEFAULT 0.0,
            predicted_reputation_impact FLOAT NOT NULL DEFAULT 0.0,
            opportunity_cost FLOAT NOT NULL DEFAULT 0.0,
            confidence FLOAT NOT NULL DEFAULT 0.0,
            simulation_twin_run_id UUID,
            simulated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS counterfactual_actualizations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            simulation_id UUID NOT NULL REFERENCES counterfactual_simulations(id) ON DELETE CASCADE,
            day_30_actual TEXT,
            day_30_accuracy_score FLOAT,
            day_90_actual TEXT,
            day_90_accuracy_score FLOAT,
            overall_calibration FLOAT,
            learnings TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── DECISION DEBT ENGINE ────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS decision_debt_assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            decision_id UUID NOT NULL REFERENCES decision_objects(id) ON DELETE CASCADE,
            debt_category TEXT NOT NULL DEFAULT 'TECHNICAL',
            debt_score FLOAT NOT NULL DEFAULT 0.0,
            description TEXT,
            expected_payoff_date DATE,
            repayment_cost_estimate FLOAT NOT NULL DEFAULT 0.0,
            repayment_priority TEXT NOT NULL DEFAULT 'MEDIUM',
            is_paid_off BOOLEAN NOT NULL DEFAULT false,
            paid_off_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS institutional_debt_index (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            week_of DATE NOT NULL UNIQUE,
            total_debt_score FLOAT NOT NULL DEFAULT 0.0,
            technical_debt FLOAT NOT NULL DEFAULT 0.0,
            operational_debt FLOAT NOT NULL DEFAULT 0.0,
            complexity_debt FLOAT NOT NULL DEFAULT 0.0,
            migration_debt FLOAT NOT NULL DEFAULT 0.0,
            dependency_debt FLOAT NOT NULL DEFAULT 0.0,
            critical_count INT NOT NULL DEFAULT 0,
            high_count INT NOT NULL DEFAULT 0,
            estimated_repayment_weeks FLOAT NOT NULL DEFAULT 0.0,
            trend TEXT NOT NULL DEFAULT 'STABLE',
            refactoring_triggered BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── CLIENT DIGITAL TWINS ────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS client_digital_twins (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL UNIQUE,
            tenant_id UUID,
            communication_preferences JSONB NOT NULL DEFAULT '{}',
            decision_speed TEXT NOT NULL DEFAULT 'methodical',
            risk_tolerance TEXT NOT NULL DEFAULT 'moderate',
            budget_authority TEXT NOT NULL DEFAULT 'unknown',
            internal_politics JSONB NOT NULL DEFAULT '{}',
            buying_psychology TEXT,
            technical_maturity TEXT NOT NULL DEFAULT 'traditional',
            support_expectation TEXT NOT NULL DEFAULT 'collaborative',
            preferred_hia_agent TEXT,
            historical_objections JSONB NOT NULL DEFAULT '[]',
            successful_strategies JSONB NOT NULL DEFAULT '[]',
            trust_score FLOAT NOT NULL DEFAULT 50.0,
            relationship_age_days INT NOT NULL DEFAULT 0,
            stakeholder_map JSONB NOT NULL DEFAULT '[]',
            churn_risk_score FLOAT NOT NULL DEFAULT 0.0,
            upsell_opportunity_score FLOAT NOT NULL DEFAULT 0.0,
            renewal_probability FLOAT NOT NULL DEFAULT 0.5,
            last_interaction_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS client_twin_interactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            twin_id UUID NOT NULL REFERENCES client_digital_twins(id) ON DELETE CASCADE,
            interaction_type TEXT NOT NULL DEFAULT 'EMAIL',
            hia_agent TEXT,
            sentiment TEXT NOT NULL DEFAULT 'neutral',
            trust_delta FLOAT NOT NULL DEFAULT 0.0,
            summary TEXT,
            profile_updates JSONB NOT NULL DEFAULT '{}',
            raw_notes TEXT,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS client_twin_predictions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            twin_id UUID NOT NULL REFERENCES client_digital_twins(id) ON DELETE CASCADE,
            model_type TEXT NOT NULL,
            confidence FLOAT NOT NULL DEFAULT 0.0,
            prediction_value FLOAT NOT NULL DEFAULT 0.0,
            prediction_label TEXT,
            historical_accuracy FLOAT NOT NULL DEFAULT 0.0,
            last_validated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── INSTITUTIONAL WISDOM INDEX ──────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS wisdom_index_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID,
            week_of DATE NOT NULL UNIQUE,
            wisdom_score FLOAT NOT NULL DEFAULT 500.0,
            previous_score FLOAT NOT NULL DEFAULT 500.0,
            delta FLOAT NOT NULL DEFAULT 0.0,
            decision_accuracy_score FLOAT NOT NULL DEFAULT 0.0,
            calibration_quality_score FLOAT NOT NULL DEFAULT 0.0,
            counterfactual_precision_score FLOAT NOT NULL DEFAULT 0.0,
            provider_authority_score FLOAT NOT NULL DEFAULT 0.0,
            pattern_reuse_score FLOAT NOT NULL DEFAULT 0.0,
            client_retention_score FLOAT NOT NULL DEFAULT 0.0,
            debt_burden_penalty FLOAT NOT NULL DEFAULT 0.0,
            knowledge_freshness_score FLOAT NOT NULL DEFAULT 0.0,
            convergence_efficiency_score FLOAT NOT NULL DEFAULT 0.0,
            self_mod_success_score FLOAT NOT NULL DEFAULT 0.0,
            narrative TEXT,
            recommendations JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── PROVIDER SOVEREIGN COUNCIL ──────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS provider_calibration_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            claim TEXT NOT NULL,
            confidence_at_claim FLOAT NOT NULL DEFAULT 0.0,
            outcome TEXT,
            was_correct BOOLEAN,
            brier_score FLOAT,
            domain_authority_weight FLOAT NOT NULL DEFAULT 1.0,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(provider_id, domain, created_at)
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS provider_council_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            trigger_type TEXT NOT NULL DEFAULT 'SCHEDULED',
            trigger_signal TEXT,
            participants JSONB NOT NULL DEFAULT '[]',
            agenda_items JSONB NOT NULL DEFAULT '[]',
            debate_rounds INT NOT NULL DEFAULT 0,
            convergence_reason TEXT,
            recommendations JSONB NOT NULL DEFAULT '[]',
            improvement_report TEXT,
            technology_adoption_report TEXT,
            competitive_threat_report TEXT,
            jarvis_decision TEXT,
            tokens_consumed INT NOT NULL DEFAULT 0,
            session_cost_usd FLOAT NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS shelved_discoveries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            summary TEXT NOT NULL,
            wake_condition TEXT NOT NULL,
            wake_metric TEXT,
            wake_threshold FLOAT,
            priority TEXT NOT NULL DEFAULT 'MEDIUM',
            roi_estimate FLOAT NOT NULL DEFAULT 0.0,
            risk_estimate FLOAT NOT NULL DEFAULT 0.0,
            is_activated BOOLEAN NOT NULL DEFAULT false,
            activated_at TIMESTAMPTZ,
            shelved_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── GRAND CONVERGENCE COUNCIL ───────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS convergence_council_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            trigger_event TEXT NOT NULL,
            trigger_type TEXT NOT NULL DEFAULT 'OPPORTUNITY',
            session_phase TEXT NOT NULL DEFAULT 'SIGNAL',
            participants JSONB NOT NULL DEFAULT '[]',
            context_loaded JSONB NOT NULL DEFAULT '{}',
            simulation_run_id UUID,
            convergence_reason TEXT,
            recommendation TEXT,
            dissenting_opinions JSONB NOT NULL DEFAULT '[]',
            jarvis_decision TEXT,
            captain_override TEXT,
            tokens_consumed INT NOT NULL DEFAULT 0,
            session_cost_usd FLOAT NOT NULL DEFAULT 0.0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS convergence_council_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES convergence_council_sessions(id) ON DELETE CASCADE,
            speaker TEXT NOT NULL,
            message TEXT NOT NULL,
            claim_type TEXT NOT NULL DEFAULT 'STATEMENT',
            confidence FLOAT NOT NULL DEFAULT 0.0,
            evidence_refs JSONB NOT NULL DEFAULT '[]',
            prediction_id UUID,
            is_falsifiable BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── MISSION AUTOPSY ENGINE ──────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS mission_autopsies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mission_id UUID NOT NULL,
            client_id UUID,
            failure_type TEXT NOT NULL DEFAULT 'MISSION_FAILURE',
            failure_summary TEXT NOT NULL,
            causal_chain JSONB NOT NULL DEFAULT '[]',
            what_failed TEXT,
            why_it_failed TEXT,
            who_detected TEXT,
            who_missed TEXT,
            which_assumption_broke TEXT,
            which_warning_ignored TEXT,
            alternative_path_that_would_succeed TEXT,
            institutional_doctrine TEXT,
            doctrine_approved BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── SENTINEL LAYER ──────────────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS sentinel_observations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'TECHNOLOGY',
            signal_strength TEXT NOT NULL DEFAULT 'WEAK',
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            url TEXT,
            raw_data JSONB NOT NULL DEFAULT '{}',
            escalated BOOLEAN NOT NULL DEFAULT false,
            escalated_to TEXT,
            council_triggered BOOLEAN NOT NULL DEFAULT false,
            council_session_id UUID,
            observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS sentinel_threat_registry (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            threat_type TEXT NOT NULL DEFAULT 'COMPETITIVE',
            threat_name TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'LOW',
            description TEXT NOT NULL,
            recommended_response TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── EXECUTIVE ACCOUNTABILITY ────────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS mission_ownership_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mission_id UUID NOT NULL UNIQUE,
            client_id UUID,
            executive_owner TEXT NOT NULL DEFAULT 'JARVIS',
            primary_hia TEXT,
            council_lead TEXT,
            department_leads JSONB NOT NULL DEFAULT '[]',
            profitability_usd FLOAT NOT NULL DEFAULT 0.0,
            client_satisfaction_score FLOAT,
            delivery_on_time BOOLEAN,
            repair_loops_count INT NOT NULL DEFAULT 0,
            delay_days INT NOT NULL DEFAULT 0,
            root_causes JSONB NOT NULL DEFAULT '[]',
            mission_status TEXT NOT NULL DEFAULT 'ACTIVE',
            mission_outcome TEXT,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── SELF-MODIFICATION REGISTRY ──────────────────────────────────────────

    op.execute("""
        CREATE TABLE IF NOT EXISTS self_modification_registry (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            mod_type TEXT NOT NULL DEFAULT 'PROMPT',
            blast_radius TEXT NOT NULL DEFAULT 'CONFIG',
            description TEXT NOT NULL,
            proposed_by TEXT NOT NULL DEFAULT 'PROVIDER_COUNCIL',
            simulation_passed BOOLEAN NOT NULL DEFAULT false,
            council_approved BOOLEAN NOT NULL DEFAULT false,
            shadow_deployed BOOLEAN NOT NULL DEFAULT false,
            ab_winner BOOLEAN,
            canary_stage TEXT NOT NULL DEFAULT 'PROPOSED',
            rollback_available BOOLEAN NOT NULL DEFAULT true,
            rollback_until TIMESTAMPTZ,
            promoted_to_primary BOOLEAN NOT NULL DEFAULT false,
            promoted_at TIMESTAMPTZ,
            rolled_back_at TIMESTAMPTZ,
            decision_object_id UUID REFERENCES decision_objects(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ─── INDEXES ─────────────────────────────────────────────────────────────

    op.execute("CREATE INDEX IF NOT EXISTS idx_decision_objects_client ON decision_objects(client_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_decision_objects_tier ON decision_objects(tier)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_decision_objects_created ON decision_objects(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_decision_options_decision ON decision_options(decision_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_digital_twins_client ON client_digital_twins(client_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sentinel_obs_category ON sentinel_observations(category)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sentinel_obs_escalated ON sentinel_observations(escalated)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_convergence_sessions_trigger ON convergence_council_sessions(trigger_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_provider_calibration_provider ON provider_calibration_records(provider_id, domain)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_wisdom_index_week ON wisdom_index_snapshots(week_of)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_self_mod_canary ON self_modification_registry(canary_stage)")


def downgrade() -> None:
    tables = [
        "self_modification_registry",
        "mission_ownership_records",
        "sentinel_threat_registry",
        "sentinel_observations",
        "mission_autopsies",
        "convergence_council_messages",
        "convergence_council_sessions",
        "shelved_discoveries",
        "provider_council_sessions",
        "provider_calibration_records",
        "wisdom_index_snapshots",
        "client_twin_predictions",
        "client_twin_interactions",
        "client_digital_twins",
        "institutional_debt_index",
        "decision_debt_assessments",
        "counterfactual_actualizations",
        "counterfactual_simulations",
        "decision_retrospectives",
        "decision_patterns",
        "decision_outcomes",
        "decision_options",
        "decision_objects",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
