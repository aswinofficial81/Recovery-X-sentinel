from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db


router = APIRouter(
    prefix="/api/revenue-leaks",
    tags=["Revenue Leaks"]
)


@router.get("")
def get_revenue_leaks(
    db: Session = Depends(get_db)
):
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
        ORDER BY revenue_impact DESC;
    """)

    result = db.execute(query)

    leaks = []

    for row in result:
        leaks.append({
            "id": str(row.id),
            "merchant_id": str(row.merchant_id),
            "leak_type": row.leak_type,
            "description": row.description,
            "segment": row.segment,
            "expected_value": float(row.expected_value),
            "actual_value": float(row.actual_value),
            "revenue_impact": float(row.revenue_impact),
            "confidence": float(row.confidence),
            "status": row.status,
            "detected_at": row.detected_at.isoformat()
                if row.detected_at else None
        })

    return {
        "count": len(leaks),
        "leaks": leaks
    }