"""
Service Registry Manager - Phase 2 orchestration layer.

Orchestrates service lifecycle: creation, instantiation, metrics tracking, and deprecation.
Bootstraps 25 existing services from CAPABILITY_MODULES into the new registry.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service_registry import (
    ServiceRegistry,
    ServiceTemplate,
    ServiceInstance,
    ServiceMetrics,
    ServiceStatus,
    ServiceType,
    ServiceDependency,
    ServiceAudit,
)
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

# Canonical 25-module service definitions (from catalog_service.py)
CANONICAL_SERVICES = [
    {
        "code": "SCOUT",
        "name": "Lead Intelligence",
        "division": "Revenue Operations",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Finds, enriches, scores, and prioritizes prospects before outreach begins.",
        "human_interface_executive": "James Whitfield",
        "agent_layer": ["Lead discovery", "ICP scoring", "market signal analysis"],
        "kpi_targets": ["20 qualified discoveries/day", "lead quality trend", "source conversion"],
    },
    {
        "code": "HERALD",
        "name": "Outreach",
        "division": "Revenue Operations",
        "service_type": ServiceType.HYBRID,
        "description": "Runs governed outreach with compliant sequencing, personalization, and response routing.",
        "human_interface_executive": "Darren Mitchell",
        "agent_layer": ["Email sequencing", "reply handling", "personalization"],
        "kpi_targets": ["48 emails/day max", "reply rate", "positive intent rate"],
    },
    {
        "code": "NEXUS-R",
        "name": "CRM Intelligence",
        "division": "Revenue Operations",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Maintains revenue truth across CRM, contacts, deals, lifecycle state, and client context.",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["CRM hygiene", "pipeline intelligence", "contact history"],
        "kpi_targets": ["clean lifecycle states", "deal velocity", "stale lead reduction"],
    },
    {
        "code": "ORACLE-S",
        "name": "Sales Forecasting",
        "division": "Revenue Operations",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Predicts revenue outcomes, deal risk, and next-best commercial actions.",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["forecast modeling", "probability scoring", "close-risk analysis"],
        "kpi_targets": ["forecast accuracy", "close probability", "pipeline risk alerts"],
    },
    {
        "code": "PRISM",
        "name": "Workflow Automation",
        "division": "AI Automation",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Turns repeatable business operations into governed automated workflows.",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["process mapping", "workflow design", "automation deployment"],
        "kpi_targets": ["manual hours removed", "automation uptime", "handoff accuracy"],
    },
    {
        "code": "ECHO",
        "name": "Agent Deployment",
        "division": "AI Automation",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Deploys specialized AI agents with clear tools, memory, permissions, and boundaries.",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["agent design", "tool routing", "capability governance"],
        "kpi_targets": ["agent success rate", "approval compliance", "fallback coverage"],
    },
    {
        "code": "PULSE",
        "name": "Voice Systems",
        "division": "AI Automation",
        "service_type": ServiceType.HYBRID,
        "description": "Creates voice-first client and operations interfaces for calls, reception, and briefings.",
        "human_interface_executive": "Lucas Reed",
        "agent_layer": ["voice intake", "call transcription", "speech synthesis"],
        "kpi_targets": ["call coverage", "handoff accuracy", "voice response latency"],
    },
    {
        "code": "SIGNAL",
        "name": "Communication",
        "division": "AI Automation",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Coordinates structured communication across Captain, clients, departments, and agents.",
        "human_interface_executive": "Lucas Reed",
        "agent_layer": ["notifications", "message routing", "communication memory"],
        "kpi_targets": ["response SLA", "message clarity", "missed-update prevention"],
    },
    {
        "code": "BRIDGE",
        "name": "Scheduling",
        "division": "AI Automation",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Connects calendar events to briefings, client context, reminders, and post-call actions.",
        "human_interface_executive": "Olivia Bennett",
        "agent_layer": ["calendar orchestration", "call prep", "meeting follow-up"],
        "kpi_targets": ["booking completion", "briefing readiness", "no-show reduction"],
    },
    {
        "code": "ATLAS-CI",
        "name": "AWS Architecture",
        "division": "Cloud & DevOps",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Designs AWS runtime foundations, networking, compute, storage, and production governance.",
        "human_interface_executive": "David Carter",
        "agent_layer": ["cloud topology", "runtime design", "AWS governance"],
        "kpi_targets": ["uptime", "cost efficiency", "deployment readiness"],
    },
    {
        "code": "NEXUS-TF",
        "name": "Terraform",
        "division": "Cloud & DevOps",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Turns cloud infrastructure into repeatable, auditable, version-controlled IaC modules.",
        "human_interface_executive": "Nathan Scott",
        "agent_layer": ["IaC modules", "state governance", "environment reproducibility"],
        "kpi_targets": ["drift prevention", "rebuild speed", "change auditability"],
    },
    {
        "code": "SIGNAL-CD",
        "name": "CI/CD",
        "division": "Cloud & DevOps",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Automates build, test, deployment, rollback, and release governance.",
        "human_interface_executive": "Nathan Scott",
        "agent_layer": ["build pipelines", "deployment gates", "rollback paths"],
        "kpi_targets": ["deploy success", "rollback time", "test gate coverage"],
    },
    {
        "code": "HELM",
        "name": "Kubernetes",
        "division": "Cloud & DevOps",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Packages scalable workloads for Kubernetes and future cloud-native orchestration.",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["cluster design", "workload orchestration", "autoscaling"],
        "kpi_targets": ["cluster health", "resource efficiency", "resilience"],
    },
    {
        "code": "RADAR",
        "name": "Observability",
        "division": "Cloud & DevOps",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Makes system health visible through telemetry, dashboards, alerts, and operational evidence.",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["metrics", "logs", "traces", "alerts"],
        "kpi_targets": ["MTTD", "MTTR", "alert precision"],
    },
    {
        "code": "CIPHER",
        "name": "Security Operations",
        "division": "Security & Compliance",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Protects cloud, application, and operational surfaces with continuous security discipline.",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["access review", "threat monitoring", "security posture"],
        "kpi_targets": ["risk reduction", "IAM hygiene", "threat response"],
    },
    {
        "code": "GUARDIAN",
        "name": "Vulnerability",
        "division": "Security & Compliance",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Finds, prioritizes, and tracks security weaknesses before they become incidents.",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["vulnerability scans", "risk ranking", "remediation tracking"],
        "kpi_targets": ["critical findings closed", "scan coverage", "risk aging"],
    },
    {
        "code": "LEDGER",
        "name": "Compliance",
        "division": "Security & Compliance",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Maintains governance evidence, decision trails, approval logs, and compliance records.",
        "human_interface_executive": "Daniel Brooks",
        "agent_layer": ["audit trail", "policy mapping", "approval evidence"],
        "kpi_targets": ["audit completeness", "policy coverage", "approval traceability"],
    },
    {
        "code": "ORACLE-BI",
        "name": "Business Intelligence",
        "division": "Intelligence & Data",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Turns operational data into executive reporting, KPI insight, and decision intelligence.",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["KPI modeling", "dashboard intelligence", "business reporting"],
        "kpi_targets": ["insight freshness", "report accuracy", "decision usefulness"],
    },
    {
        "code": "MARKET",
        "name": "Market Intelligence",
        "division": "Intelligence & Data",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Studies markets, competitors, categories, and opportunity spaces for revenue advantage.",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["market scans", "competitor tracking", "opportunity mapping"],
        "kpi_targets": ["opportunity quality", "trend detection", "market relevance"],
    },
    {
        "code": "QUANT",
        "name": "Financial Forecasting",
        "division": "Intelligence & Data",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Models financial outcomes, cash impact, revenue scenarios, and decision tradeoffs.",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["cash forecasting", "scenario modeling", "revenue simulation"],
        "kpi_targets": ["forecast confidence", "scenario coverage", "financial risk visibility"],
    },
    {
        "code": "QUILL",
        "name": "Executive Briefings",
        "division": "Intelligence & Data",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Packages complex operational context into clear Captain, client, and council briefings.",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["briefing synthesis", "meeting packs", "strategic narrative"],
        "kpi_targets": ["briefing quality", "prep time saved", "context completeness"],
    },
    {
        "code": "PORTAL",
        "name": "Client Portals",
        "division": "Digital Products",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Builds secure client-facing portals for projects, deliverables, files, and communication.",
        "human_interface_executive": "David Carter",
        "agent_layer": ["client workspace", "project visibility", "secure delivery"],
        "kpi_targets": ["client adoption", "ticket reduction", "delivery transparency"],
    },
    {
        "code": "CANVAS",
        "name": "Dashboards",
        "division": "Digital Products",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Creates operational dashboards that make system, client, and revenue state readable.",
        "human_interface_executive": "Michael Hayes",
        "agent_layer": ["dashboard UI", "live metrics", "decision screens"],
        "kpi_targets": ["load speed", "metric accuracy", "executive usability"],
    },
    {
        "code": "VISION",
        "name": "Data Visualization",
        "division": "Digital Products",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Transforms raw data into visual stories, charts, maps, and decision-ready interfaces.",
        "human_interface_executive": "Emma Collins",
        "agent_layer": ["visual analytics", "charts", "storytelling"],
        "kpi_targets": ["clarity", "signal density", "insight discovery"],
    },
    {
        "code": "COUNCIL",
        "name": "AIONX Strategic Intelligence",
        "division": "Strategic Intelligence",
        "service_type": ServiceType.AUTONOMOUS,
        "description": "Coordinates AIONX strategic reasoning, executive decision support, and governance intelligence.",
        "human_interface_executive": "Sophia Reynolds",
        "agent_layer": ["council synthesis", "strategic arbitration", "governance memory"],
        "kpi_targets": ["decision quality", "council consensus", "governed autonomy"],
    },
]


class ServiceRegistryManager:
    """
    Orchestrates service lifecycle within the dynamic registry.

    Manages:
    - Service creation and registration
    - Template creation and reuse
    - Instance instantiation and deployment
    - Metrics tracking and aggregation
    - Deprecation workflows
    - Service dependencies
    """

    def __init__(self, db: AsyncSession, tenant_id: UUID, actor: str = "system"):
        self.db = db
        self.tenant_id = tenant_id
        self.actor = actor

    async def bootstrap_canonical_services(self) -> Dict[str, Any]:
        """Bootstrap all 25 canonical services into registry. Returns summary."""
        result = {"created": [], "skipped": [], "errors": []}

        for service_def in CANONICAL_SERVICES:
            try:
                service = await self.get_or_create_service(service_def)
                result["created"].append(service_def["code"])
            except Exception as e:
                logger.error(f"Failed to bootstrap service {service_def['code']}: {e}")
                result["errors"].append({"code": service_def["code"], "error": str(e)})

        await self.db.commit()
        logger.info(f"Bootstrap complete: {len(result['created'])} services created")
        return {
            "status": "bootstrap_complete",
            "total_canonical": len(CANONICAL_SERVICES),
            "created_count": len(result["created"]),
            "error_count": len(result["errors"]),
            "details": result,
        }

    async def get_or_create_service(self, service_def: Dict[str, Any]) -> ServiceRegistry:
        """Get existing service or create new one from definition."""
        existing = await self.db.scalar(
            select(ServiceRegistry).where(
                and_(
                    ServiceRegistry.code == service_def["code"],
                    ServiceRegistry.tenant_id == self.tenant_id,
                )
            )
        )

        if existing:
            return existing

        service = ServiceRegistry(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            code=service_def["code"],
            name=service_def["name"],
            division=service_def["division"],
            description=service_def.get("description"),
            version="1.0.0",
            status=ServiceStatus.ACTIVE,
            service_type=service_def.get("service_type", ServiceType.AUTONOMOUS),
            human_interface_executive=service_def.get("human_interface_executive"),
            agent_layer=service_def.get("agent_layer", []),
            kpi_targets=service_def.get("kpi_targets", []),
            capability_flags={},
            dependencies=None,
            success_rate=None,
            avg_execution_time_ms=None,
            monthly_cost=None,
            tags=["canonical", "v1"],
            metadata={"bootstrap_source": "CAPABILITY_MODULES", "canonical_index": service_def.get("canonical_index")},
        )

        self.db.add(service)
        await self.db.flush()

        # Log audit trail
        await self._audit_log("created", service.id, f"Bootstrapped service: {service.code}")

        return service

    async def create_service_template(
        self,
        template_name: str,
        base_service_code: str,
        configuration: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> ServiceTemplate:
        """Create reusable template for service instantiation."""
        template = ServiceTemplate(
            id=uuid.uuid4(),
            template_name=template_name,
            base_service_code=base_service_code,
            description=kwargs.get("description"),
            configuration=configuration or {},
            required_capabilities=kwargs.get("required_capabilities", []),
            optional_capabilities=kwargs.get("optional_capabilities", []),
            docker_image=kwargs.get("docker_image"),
            environment_template=kwargs.get("environment_template"),
            agent_requirements=kwargs.get("agent_requirements"),
            model_preferences=kwargs.get("model_preferences"),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def instantiate_service(
        self,
        service_id: UUID,
        instance_name: str,
        template_id: Optional[UUID] = None,
        configuration: Optional[Dict[str, Any]] = None,
        environment: Optional[Dict[str, Any]] = None,
        deployment_region: Optional[str] = None,
    ) -> ServiceInstance:
        """Create running instance of a service."""
        instance = ServiceInstance(
            id=uuid.uuid4(),
            tenant_id=self.tenant_id,
            service_id=service_id,
            template_id=template_id,
            instance_name=instance_name,
            status=ServiceStatus.BETA,
            configuration=configuration or {},
            environment=environment or {},
            deployment_region=deployment_region or "ap-south-2",
            is_healthy=1,
        )
        self.db.add(instance)
        await self.db.flush()

        # Log audit trail
        await self._audit_log(
            "instantiated", service_id, f"Created instance: {instance_name}"
        )

        return instance

    async def initialize_service_instance(
        self, instance_id: UUID
    ) -> ServiceInstance:
        """Initialize and deploy service instance."""
        instance = await self.db.scalar(
            select(ServiceInstance).where(ServiceInstance.id == instance_id)
        )

        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        instance.deployed_at = datetime.utcnow()
        instance.is_healthy = 1
        instance.status = ServiceStatus.ACTIVE

        await self.db.flush()

        # Log audit trail
        await self._audit_log(
            "deployed", instance.service_id, f"Deployed instance: {instance.instance_name}"
        )

        return instance

    async def record_metrics(
        self,
        service_id: UUID,
        total_executions: int = 0,
        successful_executions: int = 0,
        failed_executions: int = 0,
        avg_execution_time_ms: Optional[int] = None,
        error_rate: Optional[float] = None,
        daily_cost: Optional[float] = None,
        active_users: Optional[int] = None,
    ) -> ServiceMetrics:
        """Record daily metrics snapshot for service."""
        success_rate = None
        if total_executions > 0:
            success_rate = (successful_executions / total_executions) * 100

        metrics = ServiceMetrics(
            id=uuid.uuid4(),
            service_id=service_id,
            metric_date=datetime.utcnow(),
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            success_rate=success_rate,
            avg_execution_time_ms=avg_execution_time_ms,
            error_rate=error_rate,
            daily_cost=daily_cost,
            active_users=active_users,
        )
        self.db.add(metrics)
        await self.db.flush()
        return metrics

    async def add_dependency(
        self,
        service_id: UUID,
        depends_on_service_id: UUID,
        dependency_type: str = "operational",
        is_critical: bool = False,
    ) -> ServiceDependency:
        """Register service-to-service dependency."""
        dependency = ServiceDependency(
            id=uuid.uuid4(),
            service_id=service_id,
            depends_on_service_id=depends_on_service_id,
            dependency_type=dependency_type,
            is_critical=1 if is_critical else 0,
        )
        self.db.add(dependency)
        await self.db.flush()
        return dependency

    async def deprecate_service(
        self, service_id: UUID, reason: str = "No longer supported"
    ) -> ServiceRegistry:
        """Initiate service deprecation workflow."""
        service = await self.db.scalar(
            select(ServiceRegistry).where(ServiceRegistry.id == service_id)
        )

        if not service:
            raise ValueError(f"Service {service_id} not found")

        service.status = ServiceStatus.DEPRECATED
        service.deprecated_at = datetime.utcnow()

        await self.db.flush()

        # Log audit trail
        await self._audit_log(
            "deprecated", service_id, f"Deprecation: {reason}"
        )

        return service

    async def get_service_by_code(self, code: str) -> Optional[ServiceRegistry]:
        """Retrieve service by code."""
        return await self.db.scalar(
            select(ServiceRegistry).where(
                and_(
                    ServiceRegistry.code == code,
                    ServiceRegistry.tenant_id == self.tenant_id,
                )
            )
        )

    async def get_all_services(
        self, status: Optional[ServiceStatus] = None
    ) -> List[ServiceRegistry]:
        """Retrieve all services, optionally filtered by status."""
        query = select(ServiceRegistry).where(
            ServiceRegistry.tenant_id == self.tenant_id
        )
        if status:
            query = query.where(ServiceRegistry.status == status)
        query = query.order_by(ServiceRegistry.name)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_service_instances(
        self, service_id: UUID
    ) -> List[ServiceInstance]:
        """Retrieve all instances of a service."""
        result = await self.db.execute(
            select(ServiceInstance).where(ServiceInstance.service_id == service_id)
        )
        return result.scalars().all()

    async def get_service_metrics_latest(
        self, service_id: UUID, days: int = 30
    ) -> List[ServiceMetrics]:
        """Retrieve latest metrics for service."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = await self.db.execute(
            select(ServiceMetrics)
            .where(
                and_(
                    ServiceMetrics.service_id == service_id,
                    ServiceMetrics.metric_date >= cutoff_date,
                )
            )
            .order_by(ServiceMetrics.metric_date.desc())
        )
        return result.scalars().all()

    async def get_service_dependencies(
        self, service_id: UUID
    ) -> List[ServiceDependency]:
        """Retrieve all dependencies of a service."""
        result = await self.db.execute(
            select(ServiceDependency).where(ServiceDependency.service_id == service_id)
        )
        return result.scalars().all()

    async def _audit_log(
        self,
        action: str,
        service_id: Optional[UUID],
        change_description: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
    ) -> ServiceAudit:
        """Log audit trail entry for service changes."""
        audit = ServiceAudit(
            id=uuid.uuid4(),
            service_id=service_id,
            action=action,
            actor=self.actor,
            timestamp=datetime.utcnow(),
            change_description=change_description,
            before_state=before_state,
            after_state=after_state,
            metadata={"tenant_id": str(self.tenant_id)},
        )
        self.db.add(audit)
        await self.db.flush()
        return audit
