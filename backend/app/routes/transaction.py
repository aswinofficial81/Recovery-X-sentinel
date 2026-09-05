from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db

router = APIRouter(
    prefix="/api/transactions",
    tags=["Transactions"]
)


@router.get("")
def get_transactions(
    status: str | None = Query(default=None),
    payment_method: str | None = Query(default=None),
    device: str | None = Query(default=None),
    location: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    offset = (page - 1) * limit

    query = text("""
        SELECT
            id,
            merchant_id,
            customer_id,
            amount,
            currency,
            status,
            payment_method,
            device,
            location,
            created_at
        FROM transactions
        WHERE
            (:status IS NULL OR status = :status)
            AND (:payment_method IS NULL OR payment_method = :payment_method)
            AND (:device IS NULL OR device = :device)
            AND (:location IS NULL OR location = :location)
        ORDER BY created_at DESC
        LIMIT :limit
        OFFSET :offset;
    """)

    result = db.execute(
        query,
        {
            "status": status,
            "payment_method": payment_method,
            "device": device,
            "location": location,
            "limit": limit,
            "offset": offset
        }
    )

    transactions = []

    for row in result:
        transactions.append({
            "id": str(row.id),
            "merchant_id": str(row.merchant_id),
            "customer_id": str(row.customer_id),
            "amount": float(row.amount),
            "currency": row.currency,
            "status": row.status,
            "payment_method": row.payment_method,
            "device": row.device,
            "location": row.location,
            "created_at": row.created_at.isoformat()
            if row.created_at else None
        })

    return {
        "page": page,
        "limit": limit,
        "count": len(transactions),
        "transactions": transactions
    }