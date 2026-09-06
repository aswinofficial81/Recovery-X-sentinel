from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.auth import get_current_merchant
from ml.models.revenue_risk import calculate_all_revenue_risks


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("")
def get_dashboard(
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    merchant_id = merchant["id"]

    transaction_query = text("""
        SELECT
            COUNT(*) AS total_transactions,

            COUNT(*) FILTER (
                WHERE status = 'SUCCESS'
            ) AS successful_transactions,

            COUNT(*) FILTER (
                WHERE status = 'FAILED'
            ) AS failed_transactions,

            COALESCE(
                SUM(amount) FILTER (
                    WHERE status = 'SUCCESS'
                ),
                0
            ) AS total_revenue

        FROM transactions

        WHERE merchant_id = :merchant_id;
    """)

    transaction_result = db.execute(
        transaction_query,
        {"merchant_id": merchant_id}
    ).mappings().one()

    leak_query = text("""
        SELECT
            COUNT(*) AS open_leaks,

            COALESCE(
                SUM(revenue_impact),
                0
            ) AS total_revenue_at_risk

        FROM revenue_leaks

        WHERE merchant_id = :merchant_id
          AND status = 'OPEN';
    """)

    leak_result = db.execute(
        leak_query,
        {"merchant_id": merchant_id}
    ).mappings().one()

    # Dynamically compute total net revenue at risk across active incidents for this merchant
    try:
        dynamic_risks = calculate_all_revenue_risks(merchant_id=merchant_id, db=db)
        incident_metrics = dynamic_risks.get("incidents", {})
        total_revenue_at_risk = sum(
            float(inc.get("revenue_at_risk", 0.0))
            for inc in incident_metrics.values()
        )
    except Exception as e:
        print(f"[DASHBOARD] Dynamic risk calculation fallback: {e}", flush=True)
        total_revenue_at_risk = float(leak_result["total_revenue_at_risk"])

    total_transactions = transaction_result["total_transactions"]
    successful_transactions = transaction_result["successful_transactions"]

    success_rate = (
        successful_transactions / total_transactions * 100
        if total_transactions > 0
        else 0
    )

    return {
        "merchant": {
            "id": merchant["id"],
            "name": merchant["name"],
            "email": merchant["email"]
        },
        "total_transactions": total_transactions,
        "successful_transactions": successful_transactions,
        "failed_transactions": transaction_result["failed_transactions"],
        "success_rate": round(success_rate, 2),
        "total_revenue": float(transaction_result["total_revenue"]),
        "open_leaks": leak_result["open_leaks"],
        "total_revenue_at_risk": round(total_revenue_at_risk, 2)
    }