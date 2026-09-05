from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db

router = APIRouter(
    prefix="/api/audit-logs",
    tags=["Audit Logs"]
)

MERCHANT_ID = "3efe1ed9-6767-47ca-9f2e-27bada51fb81"


@router.get("")
def get_audit_logs(
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            id,
            merchant_id,
            transaction_id,
            event_type,
            actor,
            details,
            created_at
        FROM audit_logs
        WHERE merchant_id = :merchant_id
        ORDER BY created_at DESC
        LIMIT 100
    """)

    rows = db.execute(
        query,
        {"merchant_id": MERCHANT_ID}
    ).mappings().all()

    logs = []
    for row in rows:
        created_at_val = row.get("created_at")
        if hasattr(created_at_val, "isoformat"):
            created_at_str = created_at_val.isoformat()
        else:
            created_at_str = str(created_at_val) if created_at_val else ""

        logs.append({
            "id": str(row["id"]) if row.get("id") else None,
            "merchant_id": str(row["merchant_id"]) if row.get("merchant_id") else None,
            "transaction_id": str(row["transaction_id"]) if row.get("transaction_id") else None,
            "event_type": row.get("event_type"),
            "actor": row.get("actor"),
            "details": row.get("details") or {},
            "created_at": created_at_str
        })

    return {
        "count": len(logs),
        "logs": logs
    }
