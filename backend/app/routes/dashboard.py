from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


MERCHANT_ID = "3efe1ed9-6767-47ca-9f2e-27bada51fb81"


@router.get("")
def get_dashboard(
    db: Session = Depends(get_db)
):

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
        {"merchant_id": MERCHANT_ID}
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
        {"merchant_id": MERCHANT_ID}
    ).mappings().one()

    total_transactions = transaction_result["total_transactions"]
    successful_transactions = transaction_result["successful_transactions"]

    success_rate = (
        successful_transactions / total_transactions * 100
        if total_transactions > 0
        else 0
    )

    return {
        "total_transactions": total_transactions,
        "successful_transactions": successful_transactions,
        "failed_transactions": transaction_result["failed_transactions"],
        "success_rate": round(success_rate, 2),
        "total_revenue": float(transaction_result["total_revenue"]),
        "open_leaks": leak_result["open_leaks"],
        "total_revenue_at_risk": float(
            leak_result["total_revenue_at_risk"]
        )
    }