from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.auth import get_current_merchant
from ml.models.recovery_executor import execute_recovery
from ml.models.recovery_executor import verify_recovery
from agent.recovery_agent import analyze_recovery
from ml.models.revenue_risk import get_incident_revenue_risk
from ml.models.incident_clustering import classify_transaction_incident
from backend.app.services.recovery_queue import job_manager


router = APIRouter(
    prefix="/api/recovery",
    tags=["Recovery"]
)


class BatchRecoveryRequest(BaseModel):
    transaction_ids: List[str]
    strategy: Optional[str] = None


# =========================================================
# RECOVERY CONFIGURATION (PUBLIC CLIENT KEYS)
# =========================================================

@router.get("/config")
def get_recovery_config():
    """
    Returns public client configuration for Razorpay checkout.
    Only the public Key ID is returned; secrets are never exposed.
    """
    from backend.app.razorpay_client import RAZORPAY_KEY_ID
    return {
        "razorpay_key_id": RAZORPAY_KEY_ID or ""
    }


# =========================================================
# EXECUTE RECOVERY (SYNCHRONOUS)
# =========================================================

@router.post("/execute/{transaction_id}")
def execute_transaction_recovery(
    transaction_id: str,
    strategy: str,
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # 1. LOAD TRANSACTION
    # -----------------------------------------------------
    query = text("""
        SELECT
            id,
            merchant_id,
            customer_id,
            amount,
            currency,
            payment_method,
            status,
            failure_reason,
            device,
            location,
            attempt_number,
            transaction_time
        FROM transactions
        WHERE id = :transaction_id
        LIMIT 1;
    """)

    result = db.execute(
        query,
        {"transaction_id": transaction_id}
    ).mappings().first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    # -----------------------------------------------------
    # 2. VALIDATE TRANSACTION STATUS
    # -----------------------------------------------------
    if result["status"] != "FAILED":
        return {
            "success": False,
            "message": "Only failed transactions can be recovered."
        }

    # -----------------------------------------------------
    # 3. AUTONOMOUS INCIDENT CLASSIFICATION
    # -----------------------------------------------------
    inc_meta = classify_transaction_incident(
        dict(result),
        merchant_id=str(result["merchant_id"]),
        db=db
    )
    incident_type = inc_meta["incident_type"]

    # -----------------------------------------------------
    # 4. BUILD TRANSACTION OBJECT
    # -----------------------------------------------------
    transaction = {
        "transaction_id": str(result["id"]),
        "merchant_id": str(result["merchant_id"]),
        "customer_id": str(result["customer_id"]),
        "amount": float(result["amount"]),
        "currency": result["currency"],
        "payment_method": result["payment_method"],
        "status": result["status"],
        "failure_reason": result["failure_reason"],
        "device": result["device"],
        "location": result["location"],
        "retry_count": max(0, result["attempt_number"] - 1),
        "incident_type": incident_type
    }

    # -----------------------------------------------------
    # 5. EXECUTE RECOVERY
    # -----------------------------------------------------
    recovery_result = execute_recovery(
        transaction,
        strategy
    )

    # -----------------------------------------------------
    # 6. RETURN RESULT
    # -----------------------------------------------------
    return {
        "success": True,
        "transaction": {
            "id": str(result["id"]),
            "amount": float(result["amount"]),
            "status": result["status"],
            "incident_type": incident_type
        },
        "recovery": recovery_result,
        **recovery_result
    }


# =========================================================
# BATCH ASYNCHRONOUS RECOVERY QUEUE
# =========================================================

@router.post("/queue/batch")
def enqueue_batch_recovery(
    payload: BatchRecoveryRequest,
    merchant: dict = Depends(get_current_merchant)
):
    """
    Enqueue multiple failed transactions for non-blocking asynchronous background recovery.
    """
    if not payload.transaction_ids:
        raise HTTPException(
            status_code=400,
            detail="transaction_ids list cannot be empty."
        )

    job_id = job_manager.create_batch_job(
        transaction_ids=payload.transaction_ids,
        strategy=payload.strategy,
        merchant_id=merchant["id"]
    )

    return {
        "success": True,
        "job_id": job_id,
        "status": "QUEUED",
        "total_queued": len(payload.transaction_ids),
        "message": f"Successfully enqueued {len(payload.transaction_ids)} transactions for background recovery."
    }


@router.get("/queue/jobs/{job_id}")
def get_batch_recovery_job(job_id: str):
    """
    Get live execution status and results of a background recovery batch job.
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Recovery job {job_id} not found."
        )
    return job


@router.post("/verify/{transaction_id}")
def verify_recovery_payment(transaction_id: str):
    result = verify_recovery(transaction_id)
    return result


@router.post("/analyze/{transaction_id}")
def analyze_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    print(f"[ANALYZE] request received for transaction_id={transaction_id}", flush=True)

    transaction_query = text("""
        SELECT
            id,
            merchant_id,
            customer_id,
            amount,
            currency,
            payment_method,
            status,
            failure_reason,
            device,
            location,
            attempt_number,
            transaction_time
        FROM transactions
        WHERE id = :transaction_id
        LIMIT 1;
    """)

    row = db.execute(
        transaction_query,
        {"transaction_id": transaction_id}
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found"
        )

    transaction = {
        "transaction_id": str(row["id"]),
        "merchant_id": str(row["merchant_id"]),
        "customer_id": str(row["customer_id"]),
        "amount": float(row["amount"]),
        "currency": row["currency"],
        "payment_method": row["payment_method"],
        "status": row["status"],
        "failure_reason": row["failure_reason"],
        "device": row["device"],
        "location": row["location"],
        "attempt_number": row["attempt_number"],
        "retry_count": max(0, row["attempt_number"] - 1),
        "is_high_value": float(row["amount"]) >= 10000,
        "transaction_time": row["transaction_time"]
    }

    print(f"[ANALYZE] transaction loaded: {transaction_id}", flush=True)

    # Customer History Aggregation
    history_query = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (
                WHERE status = 'FAILED'
            ) AS failures,
            COUNT(*) FILTER (
                WHERE status = 'SUCCESS'
            ) AS successes
        FROM transactions
        WHERE customer_id = :customer_id
          AND transaction_time < :transaction_time;
    """)

    history_row = db.execute(
        history_query,
        {
            "customer_id": row["customer_id"],
            "transaction_time": row["transaction_time"]
        }
    ).mappings().first()

    total_prev = history_row["total"] if history_row else 0
    failures_prev = history_row["failures"] if history_row else 0
    success_prev = history_row["successes"] if history_row else 0

    transaction["previous_transactions"] = total_prev
    transaction["previous_failures"] = failures_prev
    transaction["previous_success_rate"] = (
        success_prev / total_prev
        if total_prev > 0
        else 1.0
    )

    transaction["transaction_velocity"] = 0

    print(
        f"[ANALYZE] features generated: success_rate={transaction['previous_success_rate']}, velocity={transaction['transaction_velocity']}",
        flush=True
    )

    # Autonomous Incident Classification
    inc_meta = classify_transaction_incident(
        transaction,
        merchant_id=transaction.get("merchant_id"),
        db=db
    )
    incident_type = inc_meta["incident_type"]

    # Dynamic Revenue at Risk from risk engine
    incident_risk = get_incident_revenue_risk(
        incident_type,
        merchant_id=transaction.get("merchant_id"),
        db=db
    )
    if incident_risk and incident_risk.get("revenue_at_risk") is not None:
        dynamic_revenue_at_risk = float(incident_risk["revenue_at_risk"])
    else:
        dynamic_revenue_at_risk = float(transaction["amount"])

    result = analyze_recovery(
        transaction,
        incident_type,
        revenue_at_risk=dynamic_revenue_at_risk,
        execute=False
    )

    existing_recovery = db.execute(
        text("""
            SELECT
                id,
                transaction_id,
                action_type,
                status,
                expected_recovery,
                actual_recovery,
                razorpay_order_id,
                executed_at
            FROM recovery_actions
            WHERE transaction_id = :transaction_id
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"transaction_id": transaction["transaction_id"]}
    ).mappings().first()

    existing_dict = None
    if existing_recovery:
        exec_status = (
            "ORDER_CREATED"
            if existing_recovery["razorpay_order_id"]
            else existing_recovery["status"]
        )
        if existing_recovery["status"] == "SUCCESS":
            exec_status = "SUCCESS"

        existing_dict = {
            "recovery_id": str(existing_recovery["id"]),
            "action_id": str(existing_recovery["id"]),
            "strategy": existing_recovery["action_type"],
            "status": exec_status,
            "expected_recovery": float(
                existing_recovery["expected_recovery"] or 0
            ),
            "actual_recovery": float(
                existing_recovery["actual_recovery"] or 0
            ),
            "recovered_amount": float(
                existing_recovery["actual_recovery"] or 0
            ),
            "razorpay_order_id": existing_recovery["razorpay_order_id"],
            "order_id": existing_recovery["razorpay_order_id"],
            "executed_at": (
                existing_recovery["executed_at"].isoformat()
                if existing_recovery["executed_at"]
                else None
            )
        }

    print(
        f"[ANALYZE] response returned for transaction_id={transaction_id}",
        flush=True
    )

    return {
        "success": True,
        "transaction": transaction,
        "incident_classification": inc_meta,
        "analysis": result,
        "existing_recovery": existing_dict
    }


# =========================================================
# RECOVERY METRICS
# =========================================================

@router.get("/metrics")
def get_recovery_metrics(
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            COUNT(*) AS total_actions,

            COUNT(*) FILTER (
                WHERE ra.status = 'SUCCESS'
            ) AS successful_actions,

            COUNT(*) FILTER (
                WHERE ra.status = 'FAILED'
            ) AS failed_actions,

            COUNT(*) FILTER (
                WHERE ra.status = 'BLOCKED'
            ) AS blocked_actions,

            COUNT(*) FILTER (
                WHERE ra.status = 'EXECUTING'
            ) AS pending_actions,

            COALESCE(
                SUM(ra.expected_recovery),
                0
            ) AS total_expected_recovery,

            COALESCE(
                SUM(ra.actual_recovery),
                0
            ) AS total_actual_recovery

        FROM recovery_actions ra
        JOIN transactions t ON t.id = ra.transaction_id
        WHERE t.merchant_id = :merchant_id;
    """)

    result = db.execute(query, {"merchant_id": merchant["id"]}).mappings().one()

    expected_recovery = float(
        result["total_expected_recovery"] or 0
    )

    actual_recovery = float(
        result["total_actual_recovery"] or 0
    )

    recovery_rate = (
        actual_recovery / expected_recovery * 100
        if expected_recovery > 0
        else 0
    )

    return {
        "merchant_id": merchant["id"],
        "total_actions": result["total_actions"],
        "successful_actions": result["successful_actions"],
        "failed_actions": result["failed_actions"],
        "blocked_actions": result["blocked_actions"],
        "pending_actions": result["pending_actions"],
        "total_expected_recovery": round(
            expected_recovery,
            2
        ),
        "total_actual_recovery": round(
            actual_recovery,
            2
        ),
        "recovery_rate": round(
            recovery_rate,
            2
        )
    }


# =========================================================
# INCIDENT TRANSACTION QUEUE
# =========================================================

@router.get("/incident/{incident_type}/transaction")
def get_incident_transaction(
    incident_type: str,
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            t.id,
            t.amount,
            t.currency,
            t.payment_method,
            t.status,
            t.failure_reason,
            t.device,
            t.location,
            t.transaction_time
        FROM transactions t
        WHERE t.status = 'FAILED'
          AND t.merchant_id = :merchant_id
          AND (
                (
                    :incident_type = 'HIGH_VALUE_CARD_DEGRADATION'
                    AND t.payment_method = 'CARD'
                    AND t.device = 'IOS'
                    AND t.location = 'Mumbai'
                    AND t.amount >= 10000
                )
                OR
                (
                    :incident_type = 'UPI_DEGRADATION'
                    AND t.payment_method = 'UPI'
                    AND t.device = 'ANDROID'
                    AND t.location = 'Bengaluru'
                )
                OR
                (
                    :incident_type = 'EVENING_DEGRADATION'
                    AND EXTRACT(HOUR FROM t.transaction_time) >= 18
                    AND EXTRACT(HOUR FROM t.transaction_time) < 20
                )
            )
        ORDER BY 
            CASE WHEN t.id = '1c775d86-8d0f-409c-9968-ea3f18275fd6' THEN 0 ELSE 1 END,
            t.transaction_time DESC
        LIMIT 1
    """)

    transaction = db.execute(
        query,
        {
            "incident_type": incident_type,
            "merchant_id": merchant["id"]
        }
    ).mappings().first()

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail="No failed transaction found for this incident."
        )

    return {
        "transaction": dict(transaction)
    }


@router.get("/incident/{incident_type}/transactions")
def get_incident_transactions(
    incident_type: str,
    limit: int = 20,
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            t.id,
            t.merchant_id,
            t.customer_id,
            t.amount,
            t.currency,
            t.payment_method,
            t.status,
            t.failure_reason,
            t.device,
            t.location,
            t.attempt_number,
            t.transaction_time,
            ra.status AS recovery_status,
            ra.id AS recovery_action_id,
            ra.action_type AS recovery_strategy,
            ra.expected_recovery,
            ra.actual_recovery,
            ra.razorpay_order_id
        FROM transactions t
        LEFT JOIN (
            SELECT DISTINCT ON (transaction_id)
                id,
                transaction_id,
                action_type,
                status,
                expected_recovery,
                actual_recovery,
                razorpay_order_id,
                created_at
            FROM recovery_actions
            ORDER BY transaction_id, created_at DESC
        ) ra ON ra.transaction_id = t.id
        WHERE t.status = 'FAILED'
          AND t.merchant_id = :merchant_id
          AND (
                (
                    :incident_type = 'HIGH_VALUE_CARD_DEGRADATION'
                    AND t.payment_method = 'CARD'
                    AND t.location = 'Mumbai'
                    AND t.amount >= 10000
                )
                OR
                (
                    :incident_type = 'UPI_DEGRADATION'
                    AND t.payment_method = 'UPI'
                    AND t.device = 'ANDROID'
                    AND t.location = 'Bengaluru'
                )
                OR
                (
                    :incident_type = 'EVENING_DEGRADATION'
                    AND EXTRACT(HOUR FROM t.transaction_time) >= 18
                    AND EXTRACT(HOUR FROM t.transaction_time) < 20
                )
            )
        ORDER BY 
            CASE WHEN t.id = '1c775d86-8d0f-409c-9968-ea3f18275fd6' THEN 0 ELSE 1 END,
            t.transaction_time DESC
        LIMIT :limit;
    """)

    rows = db.execute(
        query,
        {
            "incident_type": incident_type,
            "merchant_id": merchant["id"],
            "limit": limit
        }
    ).mappings().all()

    transactions = []
    for r in rows:
        created_at_val = r.get("transaction_time")
        created_at_str = (
            created_at_val.isoformat()
            if hasattr(created_at_val, "isoformat")
            else str(created_at_val or "")
        )

        raw_rec_status = r.get("recovery_status")
        if not raw_rec_status:
            status_display = "READY"
        elif raw_rec_status == "SUCCESS":
            status_display = "RECOVERED"
        elif raw_rec_status == "EXECUTING":
            status_display = "ORDER_CREATED" if r.get("razorpay_order_id") else "RECOVERY_PENDING"
        else:
            status_display = raw_rec_status

        transactions.append({
            "id": str(r["id"]),
            "transaction_id": str(r["id"]),
            "merchant_id": str(r["merchant_id"]),
            "customer_id": str(r["customer_id"]),
            "amount": float(r["amount"] or 0.0),
            "currency": r.get("currency") or "INR",
            "payment_method": r.get("payment_method"),
            "status": r.get("status"),
            "failure_reason": r.get("failure_reason"),
            "device": r.get("device"),
            "location": r.get("location"),
            "attempt_number": r.get("attempt_number") or 1,
            "transaction_time": created_at_str,
            "recovery_status": status_display,
            "raw_recovery_status": raw_rec_status,
            "recovery_action_id": str(r["recovery_action_id"]) if r.get("recovery_action_id") else None,
            "recovery_strategy": r.get("recovery_strategy"),
            "expected_recovery": float(r["expected_recovery"]) if r.get("expected_recovery") else None,
            "actual_recovery": float(r["actual_recovery"]) if r.get("actual_recovery") else None,
            "razorpay_order_id": r.get("razorpay_order_id")
        })

    return {
        "incident_type": incident_type,
        "count": len(transactions),
        "transactions": transactions
    }


# =========================================================
# RECOVERY ACTIONS LIST
# =========================================================

@router.get("/actions")
def get_recovery_actions(
    merchant: dict = Depends(get_current_merchant),
    db: Session = Depends(get_db)
):
    query = text("""
        SELECT
            ra.id,
            ra.transaction_id,
            ra.action_type,
            ra.status,
            ra.expected_recovery,
            ra.actual_recovery,
            ra.attempt_number,
            ra.executed_at,
            ra.created_at,
            ra.razorpay_order_id,
            t.amount,
            t.currency,
            t.payment_method,
            t.failure_reason,
            t.device,
            t.location
        FROM recovery_actions ra
        JOIN transactions t
            ON t.id = ra.transaction_id
        WHERE t.merchant_id = :merchant_id
        ORDER BY ra.created_at DESC
        LIMIT 100;
    """)

    rows = db.execute(
        query,
        {"merchant_id": merchant["id"]}
    ).mappings().all()

    actions = []
    for row in rows:
        created_at_val = row.get("created_at")
        created_at_str = (
            created_at_val.isoformat()
            if hasattr(created_at_val, "isoformat")
            else str(created_at_val or "")
        )
        executed_at_val = row.get("executed_at")
        executed_at_str = (
            executed_at_val.isoformat()
            if hasattr(executed_at_val, "isoformat")
            else (str(executed_at_val) if executed_at_val else None)
        )

        actions.append({
            "id": str(row["id"]) if row.get("id") else None,
            "transaction_id": str(row["transaction_id"]) if row.get("transaction_id") else None,
            "action_type": row.get("action_type"),
            "status": row.get("status"),
            "expected_recovery": float(row.get("expected_recovery") or 0.0),
            "actual_recovery": float(row.get("actual_recovery") or 0.0),
            "attempt_number": row.get("attempt_number") or 1,
            "executed_at": executed_at_str,
            "created_at": created_at_str,
            "razorpay_order_id": row.get("razorpay_order_id"),
            "amount": float(row.get("amount") or 0.0),
            "currency": row.get("currency") or "INR",
            "payment_method": row.get("payment_method"),
            "failure_reason": row.get("failure_reason"),
            "device": row.get("device"),
            "location": row.get("location")
        })

    return {
        "merchant": {
            "id": merchant["id"],
            "name": merchant["name"]
        },
        "count": len(actions),
        "actions": actions
    }