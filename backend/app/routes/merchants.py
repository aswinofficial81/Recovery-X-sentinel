import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.auth import get_current_merchant

router = APIRouter(
    prefix="/api/merchants",
    tags=["Merchants"]
)


class MerchantCreate(BaseModel):
    name: str
    email: str


@router.get("/me")
def get_authenticated_merchant(
    merchant: dict = Depends(get_current_merchant)
):
    """
    Returns the active merchant context resolved via token, X-Merchant-ID, or demo fallback.
    """
    return {
        "status": "authenticated",
        "merchant": merchant
    }


@router.get("")
def list_merchants(
    db: Session = Depends(get_db)
):
    """
    List all registered merchants with their live leak and transaction counts.
    """
    rows = db.execute(text("""
        SELECT
            m.id,
            m.name,
            m.email,
            (SELECT COUNT(*) FROM transactions t WHERE t.merchant_id = m.id) AS total_transactions,
            (SELECT COUNT(*) FROM revenue_leaks rl WHERE rl.merchant_id = m.id AND rl.status = 'OPEN') AS open_leaks
        FROM merchants m
        ORDER BY m.name ASC;
    """)).mappings().all()

    merchants = []
    for r in rows:
        merchants.append({
            "id": str(r["id"]),
            "name": r["name"],
            "email": r["email"],
            "total_transactions": int(r["total_transactions"] or 0),
            "open_leaks": int(r["open_leaks"] or 0)
        })

    return {
        "count": len(merchants),
        "merchants": merchants
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_merchant(
    payload: MerchantCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new merchant tenant.
    """
    existing = db.execute(
        text("SELECT id FROM merchants WHERE email = :email LIMIT 1"),
        {"email": payload.email}
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Merchant with email {payload.email} already exists."
        )

    new_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO merchants (id, name, email)
            VALUES (:id, :name, :email)
        """),
        {"id": str(new_id), "name": payload.name, "email": payload.email}
    )
    db.commit()

    return {
        "success": True,
        "merchant": {
            "id": str(new_id),
            "name": payload.name,
            "email": payload.email
        }
    }
