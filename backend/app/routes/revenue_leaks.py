from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.auth import get_current_merchant
from ml.models.revenue_risk import calculate_all_revenue_risks


router = APIRouter(
    prefix="/api/revenue-leaks",
    tags=["Revenue Leaks"]
)


@router.get("")
def get_revenue_leaks(
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    merchant_id = merchant["id"]

    # Dynamically compute real-time incident risks and remaining exposure for this tenant
    dynamic_risks = calculate_all_revenue_risks(merchant_id=merchant_id, db=db)
    incident_metrics = dynamic_risks.get("incidents", {})

    query = text("""
        SELECT
            id,
            merchant_id,
            leak_type,
            description,
            segment,
            expected_value,
            actual_value,
            revenue_impact,
            confidence,
            status,
            detected_at
        FROM revenue_leaks
        WHERE merchant_id = :merchant_id
        ORDER BY revenue_impact DESC;
    """)

    result = db.execute(query, {"merchant_id": merchant_id}).fetchall()

    leaks = []

    for row in result:
        leak_type = row.leak_type
        dyn = incident_metrics.get(leak_type)

        if dyn:
            expected_val = float(dyn.get("baseline_success_rate", row.expected_value))
            actual_val = float(dyn.get("actual_success_rate", row.actual_value))
            revenue_impact = float(dyn.get("revenue_at_risk", row.revenue_impact))
            confidence = float(dyn.get("confidence", row.confidence))

            # Synchronize database table so external SQL queries stay current
            try:
                db.execute(
                    text("""
                        UPDATE revenue_leaks
                        SET
                            expected_value = :expected_value,
                            actual_value = :actual_value,
                            revenue_impact = :revenue_impact,
                            confidence = :confidence
                        WHERE id = :id;
                    """),
                    {
                        "expected_value": expected_val,
                        "actual_value": actual_val,
                        "revenue_impact": revenue_impact,
                        "confidence": confidence,
                        "id": row.id
                    }
                )
            except Exception as e:
                print(f"[REVENUE_LEAKS] Failed to update db row for {leak_type}: {e}", flush=True)
        else:
            expected_val = float(row.expected_value)
            actual_val = float(row.actual_value)
            revenue_impact = float(row.revenue_impact)
            confidence = float(row.confidence)

        leaks.append({
            "id": str(row.id),
            "merchant_id": str(row.merchant_id),
            "leak_type": row.leak_type,
            "description": row.description,
            "segment": row.segment,
            "expected_value": expected_val,
            "actual_value": actual_val,
            "revenue_impact": revenue_impact,
            "confidence": confidence,
            "status": row.status,
            "detected_at": row.detected_at.isoformat()
                if row.detected_at else None
        })

    try:
        db.commit()
    except Exception:
        db.rollback()

    # Sort descending by dynamic revenue impact
    leaks.sort(key=lambda x: x["revenue_impact"], reverse=True)

    return {
        "merchant": {
            "id": merchant["id"],
            "name": merchant["name"]
        },
        "count": len(leaks),
        "leaks": leaks
    }