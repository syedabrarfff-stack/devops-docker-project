#!/usr/bin/env python
"""
JARVIS Production Readiness Verification Checklist.

This script validates that all critical systems are ready for AWS ECS Fargate deployment.
Run this after environment variables are configured and services are running locally.

Exit codes:
  0 = All systems GO for production
  1 = Critical blocker found (cannot deploy)
  2 = Warnings found (can deploy with caution)
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Tuple, List

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class ProductionCheck:
    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []
        self.critical_failures = 0
        self.warnings = 0

    def check(self, name: str, passed: bool, detail: str = ""):
        """Record a check result."""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.checks.append((status, name, detail or ""))
        if not passed:
            self.critical_failures += 1

    def warn(self, name: str, detail: str = ""):
        """Record a warning (non-critical)."""
        self.checks.append(("⚠ WARN", name, detail or ""))
        self.warnings += 1

    def report(self) -> int:
        """Print report and return exit code."""
        print("\n" + "=" * 80)
        print("JARVIS PRODUCTION READINESS REPORT")
        print("=" * 80 + "\n")

        for status, name, detail in self.checks:
            line = f"{status:12} {name}"
            if detail:
                line += f"\n             {detail}"
            print(line)

        print("\n" + "=" * 80)
        print(f"Critical Failures: {self.critical_failures}")
        print(f"Warnings: {self.warnings}")
        print("=" * 80 + "\n")

        if self.critical_failures > 0:
            print("❌ PRODUCTION READINESS: BLOCKED")
            print("   Fix critical failures before deploying to AWS ECS Fargate.")
            return 1
        elif self.warnings > 0:
            print("⚠️  PRODUCTION READINESS: CAUTION")
            print("   System can deploy with warnings. Review before going live.")
            return 2
        else:
            print("✅ PRODUCTION READINESS: GO")
            print("   All systems verified. Ready for deployment.")
            return 0


async def run_checks():
    """Execute all production readiness checks."""
    checker = ProductionCheck()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Configuration & Environment
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking configuration and environment...\n")

    from app.core.config import settings

    # 1.1 Production Security Settings
    checker.check(
        "DEBUG mode disabled",
        settings.DEBUG == False,
        f"DEBUG={settings.DEBUG} (must be False for production)"
    )
    checker.check(
        "SECRET_KEY is not default",
        settings.SECRET_KEY not in ("change-this-in-production", ""),
        f"Using custom SECRET_KEY (length: {len(settings.SECRET_KEY)} chars)"
    )
    checker.check(
        "CAPTAIN_PASSWORD is not default",
        settings.CAPTAIN_PASSWORD not in ("CHANGE_ME_IN_ENV", "change_me", ""),
        "Using custom CAPTAIN_PASSWORD"
    )
    checker.check(
        "Database URL is not default",
        "jarvis_pass" not in settings.DATABASE_URL and "jarvis_secret" not in settings.DATABASE_URL,
        f"Using non-default database credentials"
    )

    # 1.2 Critical Service Credentials
    checker.check(
        "STRIPE_WEBHOOK_SECRET configured",
        bool(settings.STRIPE_WEBHOOK_SECRET),
        f"Webhook verification available" if settings.STRIPE_WEBHOOK_SECRET else "CRITICAL: Payment webhooks will fail"
    )
    checker.check(
        "SES_FROM_EMAIL configured",
        bool(settings.SES_FROM_EMAIL),
        f"Email sending configured" if settings.SES_FROM_EMAIL else "CRITICAL: Outreach email will fail"
    )
    checker.check(
        "AWS credentials present",
        bool(settings.AWS_ACCESS_KEY_ID) and bool(settings.AWS_SECRET_ACCESS_KEY),
        f"AWS IAM auth ready" if (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY) else "CRITICAL: AWS services unavailable"
    )
    checker.check(
        "GITHUB_TOKEN configured",
        bool(settings.GITHUB_TOKEN),
        f"GitHub API auth ready" if settings.GITHUB_TOKEN else "WARNING: Scout network cannot push to GitHub"
    )

    # 1.3 AI Providers
    from app.services.ai.router import AIRouter
    router = AIRouter()
    providers = router.available_providers()
    checker.check(
        "AI providers initialized",
        len(providers) >= 3,
        f"Available: {', '.join(sorted(providers)[:5])}" + (f" +{len(providers)-5} more" if len(providers) > 5 else "")
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Database & Schema
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking database schema...\n")

    from app.models import register_models
    from app.core.database import Base

    register_models()
    table_count = len([m for m in Base.registry.mappers if hasattr(m.class_, '__tablename__')])
    checker.check(
        "Database models registered",
        table_count >= 100,
        f"{table_count} tables registered (expected 100+)"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. API Routes
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking API routes...\n")

    from app.api.v1 import api_router

    route_count = len([r for r in api_router.routes if hasattr(r, 'path')])
    protected_count = len([r for r in api_router.routes if hasattr(r, 'dependencies') and r.dependencies])
    checker.check(
        "API routes registered",
        route_count >= 600,
        f"{route_count} routes, {protected_count} protected"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Critical Services
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking critical services...\n")

    try:
        from app.services.governance.captain_queue import captain_queue
        checker.check("Captain approval queue", True, "Service loads correctly")
    except Exception as e:
        checker.check("Captain approval queue", False, str(e)[:80])

    try:
        from app.services.governance.proposal_generator import proposal_generator
        checker.check("Proposal generator", True, "Service loads correctly")
    except Exception as e:
        checker.check("Proposal generator", False, str(e)[:80])

    try:
        from app.services.leads.scoring import lead_scoring_engine
        checker.check("Lead scoring engine", True, "Service loads correctly")
    except Exception as e:
        checker.check("Lead scoring engine", False, str(e)[:80])

    try:
        from app.services.leads.discovery import lead_discovery_engine
        checker.check("Lead discovery engine", True, "Service loads correctly")
    except Exception as e:
        checker.check("Lead discovery engine", False, str(e)[:80])

    try:
        from app.services.outreach.engine import outreach_engine
        checker.check("Outreach engine", True, "Service loads correctly")
    except Exception as e:
        checker.check("Outreach engine", False, str(e)[:80])

    try:
        from app.services.scheduler.engine import get_scheduler
        scheduler = get_scheduler()
        checker.check("APScheduler engine", True, "Ready for job registration")
    except Exception as e:
        checker.check("APScheduler engine", False, str(e)[:80])

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Docker & Infrastructure
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking Docker configuration...\n")

    docker_compose = ROOT / "docker-compose.yml"
    terraform_files = list((ROOT / "infra" / "terraform").glob("*.tf"))

    checker.check(
        "docker-compose.yml present",
        docker_compose.exists(),
        "Local development configuration ready"
    )
    checker.check(
        "Terraform IaC files present",
        len(terraform_files) > 0,
        f"{len(terraform_files)} .tf files for AWS ECS deployment"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 6. CI/CD Pipeline
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking CI/CD configuration...\n")

    github_workflows = list((ROOT / ".github" / "workflows").glob("*.yml")) if (ROOT / ".github" / "workflows").exists() else []
    checker.check(
        "GitHub Actions workflows present",
        len(github_workflows) > 0,
        f"{len(github_workflows)} workflow(s) configured"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Deployment Files
    # ─────────────────────────────────────────────────────────────────────────
    print("Checking deployment configuration...\n")

    requirements = BACKEND / "requirements.txt"
    backend_dockerfile = BACKEND / "Dockerfile"
    frontend_dockerfile = ROOT / "frontend" / "Dockerfile"

    checker.check(
        "Python requirements.txt present",
        requirements.exists(),
        "Dependencies documented for container build"
    )
    checker.check(
        "Backend Dockerfile present",
        backend_dockerfile.exists(),
        "Backend Docker image build configuration ready"
    )
    checker.check(
        "Frontend Dockerfile present",
        frontend_dockerfile.exists(),
        "Frontend Docker image build configuration ready"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Print Report
    # ─────────────────────────────────────────────────────────────────────────
    return checker.report()


async def main():
    """Run production readiness checks and exit with appropriate code."""
    exit_code = await run_checks()
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except Exception as e:
        print(f"\n❌ PRODUCTION READINESS CHECK FAILED")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
