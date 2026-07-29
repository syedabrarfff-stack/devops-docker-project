#!/usr/bin/env python
"""
JARVIS Startup Validation — Run immediately after deployment.

This script runs post-deployment health checks to confirm the system
is operational and ready to serve traffic.

Usage:
  python startup_validation.py

  Or from container:
  python -m scripts.startup_validation

Exit codes:
  0 = All checks passed — system ready
  1 = Critical failure — rollback needed
"""
import asyncio
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


async def validate():
    """Run all startup validation checks."""
    start_time = time.time()

    print("\n" + "=" * 80)
    print("JARVIS STARTUP VALIDATION")
    print("=" * 80 + "\n")

    checks = []

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Configuration Load
    # ─────────────────────────────────────────────────────────────────────────
    print("[1/8] Configuration...")
    try:
        from app.core.config import settings
        checks.append(("✓", "Settings loaded", f"v{settings.APP_VERSION}"))

        # Verify critical settings
        if settings.DEBUG:
            checks.append(("⚠", "DEBUG mode enabled", "OK for development"))
        else:
            checks.append(("✓", "DEBUG mode disabled", "Production configuration"))
    except Exception as e:
        checks.append(("✗", "Configuration failed", str(e)[:60]))
        return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Database Models
    # ─────────────────────────────────────────────────────────────────────────
    print("[2/8] Database models...")
    try:
        from app.models import register_models
        from app.core.database import Base

        register_models()
        table_count = len([m for m in Base.registry.mappers if hasattr(m.class_, '__tablename__')])
        checks.append(("✓", f"Database models registered", f"{table_count} tables"))
    except Exception as e:
        checks.append(("✗", "Model registration failed", str(e)[:60]))
        return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 3. API Routes
    # ─────────────────────────────────────────────────────────────────────────
    print("[3/8] API routes...")
    try:
        from app.api.v1 import api_router

        route_count = len([r for r in api_router.routes if hasattr(r, 'path')])
        checks.append(("✓", "API routes registered", f"{route_count} routes"))
    except Exception as e:
        checks.append(("✗", "API routes failed", str(e)[:60]))
        return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 4. AI Providers
    # ─────────────────────────────────────────────────────────────────────────
    print("[4/8] AI providers...")
    try:
        from app.services.ai.router import AIRouter

        router = AIRouter()
        providers = router.available_providers()

        if len(providers) < 3:
            checks.append(("✗", "Insufficient AI providers", f"only {len(providers)} available"))
            return checks, 1

        checks.append(("✓", f"AI providers ready", f"{len(providers)} providers"))
    except Exception as e:
        checks.append(("✗", "AI provider init failed", str(e)[:60]))
        return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Scheduler Engine
    # ─────────────────────────────────────────────────────────────────────────
    print("[5/8] Scheduler...")
    try:
        from app.services.scheduler.scheduler import get_scheduler

        scheduler = get_scheduler()
        checks.append(("✓", "Scheduler engine initialized", "Ready for jobs"))
    except Exception as e:
        checks.append(("✗", "Scheduler init failed", str(e)[:60]))
        return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Critical Services
    # ─────────────────────────────────────────────────────────────────────────
    print("[6/8] Critical services...")

    critical_services = {
        "Captain queue": "app.services.governance.captain_queue",
        "Proposals": "app.services.governance.proposal_generator",
        "Lead scoring": "app.services.leads.scoring",
        "Lead discovery": "app.services.leads.discovery",
        "Outreach": "app.services.outreach.engine",
    }

    for service_name, module_path in critical_services.items():
        try:
            __import__(module_path)
            checks.append(("✓", f"{service_name} loaded", "✓"))
        except Exception as e:
            checks.append(("✗", f"{service_name} failed", str(e)[:40]))
            return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 7. FastAPI App
    # ─────────────────────────────────────────────────────────────────────────
    print("[7/8] FastAPI app...")
    try:
        from app.main import app

        # Verify the app has the API router
        has_api_router = any(
            hasattr(route, 'path') and '/api/v1' in str(route.path)
            for route in app.routes
        )

        if has_api_router:
            checks.append(("✓", "FastAPI app ready", "With API v1 routes"))
        else:
            checks.append(("⚠", "FastAPI app", "API routes not found (might be included later)"))
    except Exception as e:
        checks.append(("✗", "FastAPI app failed", str(e)[:60]))
        return checks, 1

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Environment Configuration
    # ─────────────────────────────────────────────────────────────────────────
    print("[8/8] Environment...")

    from app.core.config import settings

    env_checks = [
        ("SECRET_KEY set", settings.SECRET_KEY not in ("change-this-in-production", "")),
        ("CAPTAIN_PASSWORD set", settings.CAPTAIN_PASSWORD not in ("CHANGE_ME_IN_ENV", "")),
        ("Database configured", "sqlite" in settings.DATABASE_URL or "postgresql" in settings.DATABASE_URL),
    ]

    for check_name, passed in env_checks:
        status = "✓" if passed else "⚠"
        checks.append((status, check_name, "OK" if passed else "Using default"))

    # ─────────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    failed = len([c for c in checks if c[0] == "✗"])
    warnings = len([c for c in checks if c[0] == "⚠"])

    return checks, 0 if failed == 0 else 1, elapsed, warnings


async def main():
    """Execute validation and print report."""
    result = await validate()

    if len(result) == 4:
        checks, exit_code, elapsed, warnings = result
    else:
        checks, exit_code = result
        elapsed = 0
        warnings = 0

    # Print results
    print("\n" + "─" * 80)
    for status, name, detail in checks:
        line = f"{status}  {name:<40} {detail}"
        print(line)

    print("─" * 80)
    failed_count = len([c for c in checks if c[0] == "✗"])
    print(f"\n✅ Startup validation completed in {elapsed:.2f}s")
    print(f"  Passed: {len(checks) - failed_count - warnings}")
    print(f"  Warnings: {warnings}")
    print(f"  Failed: {failed_count}")

    if failed_count == 0:
        print("\n🚀 SYSTEM READY FOR TRAFFIC")
        print("=" * 80 + "\n")
        return 0
    else:
        print("\n❌ STARTUP VALIDATION FAILED")
        print("   Fix critical issues before serving traffic")
        print("=" * 80 + "\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ VALIDATION CRASH: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
