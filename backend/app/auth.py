import os
import uuid
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db

DEFAULT_MERCHANT_EMAIL = "demo@example.com"
FALLBACK_MERCHANT_ID = "3efe1ed9-6767-47ca-9f2e-27bada51fb81"


def get_current_merchant(
    request: Request,
    db: Session = Depends(get_db)
) -> dict:
    """
    Multi-tenant merchant resolver dependency.

    Resolution Priority:
    1. Header `X-Merchant-ID`
    2. Header `Authorization: Bearer <merchant_id_or_token>`
    3. Query parameter `?merchant_id=`
    4. Seamless fallback to Demo Merchant (`demo@example.com` or first merchant)
    """
    merchant_id_candidate: Optional[str] = None

    # 1. Header: X-Merchant-ID
    x_merchant_id = request.headers.get("X-Merchant-ID")
    if x_merchant_id:
        merchant_id_candidate = x_merchant_id.strip()

    # 2. Header: Authorization: Bearer <id>
    if not merchant_id_candidate:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            # If the token is a valid UUID or format, treat as merchant_id
            try:
                uuid.UUID(token)
                merchant_id_candidate = token
            except ValueError:
                pass

    # 3. Query param: ?merchant_id=
    if not merchant_id_candidate:
        qp = request.query_params.get("merchant_id")
        if qp:
            merchant_id_candidate = qp.strip()

    # If a specific merchant was requested, validate in DB
    if merchant_id_candidate:
        try:
            m_uuid = uuid.UUID(merchant_id_candidate)
            merchant_row = db.execute(
                text("SELECT id, name, email FROM merchants WHERE id = :id LIMIT 1"),
                {"id": str(m_uuid)}
            ).mappings().first()

            if merchant_row:
                return {
                    "id": str(merchant_row["id"]),
                    "name": merchant_row["name"],
                    "email": merchant_row["email"]
                }
        except (ValueError, Exception):
            pass

    # 4. Fallback: Demo Merchant
    demo_row = db.execute(
        text("SELECT id, name, email FROM merchants WHERE email = :email LIMIT 1"),
        {"email": DEFAULT_MERCHANT_EMAIL}
    ).mappings().first()

    if demo_row:
        return {
            "id": str(demo_row["id"]),
            "name": demo_row["name"],
            "email": demo_row["email"]
        }

    # 5. Last-resort fallback: first available merchant
    first_row = db.execute(
        text("SELECT id, name, email FROM merchants ORDER BY created_at ASC LIMIT 1")
    ).mappings().first()

    if first_row:
        return {
            "id": str(first_row["id"]),
            "name": first_row["name"],
            "email": first_row["email"]
        }

    # If DB is completely empty of merchants
    return {
        "id": FALLBACK_MERCHANT_ID,
        "name": "Demo Electronics",
        "email": DEFAULT_MERCHANT_EMAIL
    }
