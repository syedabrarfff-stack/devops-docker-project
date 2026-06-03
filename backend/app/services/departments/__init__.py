"""
Departments — 6-Layer Autonomous Intelligence System

Layer 1: Department Intelligence Officers (DIO)
Layer 2: Council Intelligence Loop (milestone → PDF → Council → improvement)
Layer 3: Outreach Intelligence Loop (every email reviewed by Council)
Layer 4: Technology Evolution Engine (24/7 monitoring)
Layer 5: Client Call Intelligence (ElevenLabs voice + Council briefing)
Layer 6: Strategy Oversight Team (daily report → Council → cascade)
"""
from app.services.departments.department_agent_service import DepartmentAgentService, department_agent_service
from app.services.departments.milestone_engine import MilestoneEngine, milestone_engine
from app.services.departments.tech_evolution_engine import TechEvolutionEngine, tech_evolution_engine
from app.services.departments.call_intelligence_service import CallIntelligenceService, call_intelligence_service
from app.services.departments.strategy_report_service import StrategyReportService, strategy_report_service

__all__ = [
    "DepartmentAgentService", "department_agent_service",
    "MilestoneEngine", "milestone_engine",
    "TechEvolutionEngine", "tech_evolution_engine",
    "CallIntelligenceService", "call_intelligence_service",
    "StrategyReportService", "strategy_report_service",
]
