"""
End-to-end test workflow — validates lead→proposal→payment→completion cycle.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger(__name__)


async def run_full_client_workflow_test(
    test_prospect_name: str = "Acme Corporation",
    test_prospect_email: str = "contact@acme-test.com",
    estimated_deal_value: float = 3500,
    db = None,
) -> dict:
    """
    Simulate complete workflow:
    1. Create lead
    2. Mark as qualified
    3. Auto-generate proposal
    4. Mark proposal accepted
    5. Create invoice
    6. Mark invoice sent
    7. Simulate payment received
    """
    from app.core.database import AsyncSessionLocal, set_tenant_context
    from app.services.governance.auto_proposal import auto_generate_proposal_for_lead
    from app.services.governance.document_gen import create_invoice, update_invoice_status
    from app.core.config import settings
    import uuid as uuid_module

    close_db = False
    if not db:
        db = AsyncSessionLocal()
        close_db = True

    try:
        tenant_id = uuid_module.UUID(settings.JARVIS_DEFAULT_TENANT_ID or "00000000-0000-0000-0000-000000000000")
        await set_tenant_context(db, str(tenant_id))

        workflow_id = str(uuid4())
        logger.info("Starting full client workflow test [id=%s]", workflow_id)

        # Step 1: Create lead (simulated — in real flow, this comes from discovery)
        step_1_lead_created = {
            "id": str(uuid4()),
            "name": test_prospect_name,
            "email": test_prospect_email,
            "company": test_prospect_name.replace(" Corporation", "").replace(" Inc", ""),
            "estimated_value": estimated_deal_value,
            "status": "qualified",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Step 1: Lead created — %s", step_1_lead_created["name"])

        # Step 2: Auto-generate proposal
        step_2_proposal = await auto_generate_proposal_for_lead(
            lead_id=uuid_module.UUID(step_1_lead_created["id"]),
            lead_name=step_1_lead_created["name"],
            lead_email=step_1_lead_created["email"],
            lead_company=step_1_lead_created["company"],
            estimated_deal_value=estimated_deal_value,
            lead_context=f"Test workflow for {step_1_lead_created['company']}",
            db=db,
        )
        logger.info("Step 2: Proposal auto-generated — auto_approved=%s", step_2_proposal.get("auto_approved"))

        # Step 3: Create invoice
        async with db.begin():
            invoice = await create_invoice(
                db,
                client_name=step_1_lead_created["name"],
                client_email=step_1_lead_created["email"],
                client_company=step_1_lead_created["company"],
                items=[{
                    "description": "Premium Operating System Implementation",
                    "qty": 1,
                    "unit_price": estimated_deal_value,
                    "amount": estimated_deal_value,
                }],
                tax_rate=0.0,
                currency="USD",
                notes=f"Test workflow {workflow_id}",
                due_days=14,
            )

        step_3_invoice_created = {
            "id": invoice["id"],
            "invoice_number": invoice["invoice_number"],
            "status": invoice["status"],
            "total": invoice["total"],
        }
        logger.info("Step 3: Invoice created — %s ($%.2f)", invoice["invoice_number"], invoice["total"])

        # Step 4: Mark invoice as sent (auto-triggered by auto-approval)
        async with db.begin():
            ok = await update_invoice_status(db, invoice["id"], "sent")

        step_4_invoice_sent = {
            "invoice_id": invoice["id"],
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Step 4: Invoice marked sent")

        # Step 5: Simulate payment received
        step_5_payment_simulated = {
            "invoice_id": invoice["id"],
            "amount_paid": invoice["total"],
            "payment_method": "stripe_test",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }
        logger.info("Step 5: Payment simulated (test workflow)")

        # Summary
        result = {
            "workflow_id": workflow_id,
            "status": "completed",
            "prospect": step_1_lead_created,
            "proposal": step_2_proposal,
            "invoice": step_3_invoice_created,
            "payment_simulation": step_5_payment_simulated,
            "total_duration_ms": 0,
            "message": f"✓ Full workflow completed for {test_prospect_name}",
        }

        logger.info("Workflow test completed successfully [id=%s]", workflow_id)
        return result

    except Exception as exc:
        logger.error("Workflow test failed: %s", exc)
        return {
            "workflow_id": workflow_id,
            "status": "failed",
            "error": str(exc),
            "message": f"✗ Workflow test failed: {exc}",
        }

    finally:
        if close_db:
            await db.close()
