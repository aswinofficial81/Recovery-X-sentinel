import uuid
import time
import threading
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from backend.app.database import SessionLocal


class RecoveryJobManager:
    """
    In-memory asynchronous background recovery queue manager.
    Coordinates batch recovery executions without blocking HTTP request threads.
    """

    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="recoverx-worker")
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_batch_job(
        self,
        transaction_ids: List[str],
        strategy: Optional[str] = None,
        merchant_id: Optional[str] = None
    ) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = time.time()

        with self.lock:
            self.jobs[job_id] = {
                "job_id": job_id,
                "merchant_id": merchant_id,
                "strategy": strategy or "AUTO_RECOMMENDED",
                "status": "QUEUED",
                "total_transactions": len(transaction_ids),
                "processed_count": 0,
                "successful_count": 0,
                "failed_count": 0,
                "total_expected_recovery": 0.0,
                "created_at": now,
                "completed_at": None,
                "results": [],
                "errors": []
            }

        # Spawn background execution
        self.executor.submit(self._execute_batch, job_id, transaction_ids, strategy, merchant_id)
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.jobs.get(job_id)

    def _execute_batch(
        self,
        job_id: str,
        transaction_ids: List[str],
        default_strategy: Optional[str],
        merchant_id: Optional[str]
    ):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "PROCESSING"

        from ml.models.strategy_ranking import rank_strategies
        from ml.models.recovery_executor import execute_recovery
        from ml.models.incident_clustering import classify_transaction_incident
        from sqlalchemy import text

        for tx_id in transaction_ids:
            try:
                with SessionLocal() as db:
                    # 1. Fetch transaction
                    query = text("""
                        SELECT
                            id, merchant_id, customer_id, amount, currency,
                            payment_method, status, failure_reason, device,
                            location, attempt_number, transaction_time
                        FROM transactions
                        WHERE id = :id
                        LIMIT 1
                    """)
                    row = db.execute(query, {"id": tx_id}).mappings().first()

                    if not row:
                        with self.lock:
                            self.jobs[job_id]["processed_count"] += 1
                            self.jobs[job_id]["failed_count"] += 1
                            self.jobs[job_id]["errors"].append(f"Transaction {tx_id} not found")
                        continue

                    # 2. Build transaction object
                    tx = {
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
                        "transaction_time": row["transaction_time"]
                    }

                    # 3. Classify incident
                    inc_meta = classify_transaction_incident(tx, merchant_id=merchant_id, db=db)
                    tx["incident_type"] = inc_meta["incident_type"]

                    # 4. Resolve strategy
                    strategy = default_strategy
                    if not strategy or strategy == "AUTO_RECOMMENDED":
                        rankings = rank_strategies(tx)
                        strategy = rankings[0]["strategy"] if rankings else "ALTERNATIVE_PAYMENT"

                    # 5. Execute recovery
                    exec_result = execute_recovery(tx, strategy)

                    with self.lock:
                        job = self.jobs[job_id]
                        job["processed_count"] += 1
                        is_ok = exec_result.get("success", False) or exec_result.get("status") in ("EXECUTING", "SUCCESS")
                        if is_ok:
                            job["successful_count"] += 1
                            exp_rec = float(exec_result.get("expected_recovery") or 0.0)
                            job["total_expected_recovery"] += exp_rec
                        else:
                            job["failed_count"] += 1

                        job["results"].append({
                            "transaction_id": tx_id,
                            "strategy": strategy,
                            "status": exec_result.get("status"),
                            "expected_recovery": exec_result.get("expected_recovery"),
                            "razorpay_order_id": exec_result.get("razorpay_order_id")
                        })

            except Exception as e:
                with self.lock:
                    job = self.jobs[job_id]
                    job["processed_count"] += 1
                    job["failed_count"] += 1
                    job["errors"].append(f"Error executing {tx_id}: {str(e)}")

        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "COMPLETED"
                self.jobs[job_id]["completed_at"] = time.time()


# Singleton background manager
job_manager = RecoveryJobManager(max_workers=4)
