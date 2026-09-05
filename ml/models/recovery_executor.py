import os
import sys
import uuid
import json
from datetime import datetime


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../.."
    )
)

sys.path.insert(0, PROJECT_ROOT)


# =========================================================
# IMPORT POLICY ENGINE
# =========================================================

from ml.models.policy_engine import evaluate_policy


# =========================================================
# IMPORT DATABASE
# =========================================================

from sqlalchemy import text

from backend.app.database import SessionLocal


# =========================================================
# IMPORT RAZORPAY CLIENT
# =========================================================

from backend.app.razorpay_client import (
    create_test_order,
    fetch_order
)

# =========================================================
# RECOVERY EXECUTOR
# =========================================================

print("\n========================================")
print("        RECOVERY EXECUTOR")
print("========================================")


# =========================================================
# PERSIST EXECUTION TO DATABASE
# =========================================================

def persist_execution(
    transaction,
    strategy,
    result
):

    transaction_id = transaction.get(
        "transaction_id"
    )

    merchant_id = transaction.get(
        "merchant_id"
    )


    # -----------------------------------------------------
    # Validate PostgreSQL UUIDs
    # -----------------------------------------------------

    try:

        transaction_uuid = uuid.UUID(
            str(transaction_id)
        )

        merchant_uuid = uuid.UUID(
            str(merchant_id)
        )

    except (
        ValueError,
        TypeError,
        AttributeError
    ):

        print(
            "\n→ Database persistence skipped "
            "(test transaction does not contain valid UUIDs)"
        )

        return


    db = SessionLocal()


    try:

        # =================================================
        # 1. INSERT RECOVERY ACTION
        # =================================================

        recovery_query = text("""
            INSERT INTO recovery_actions (
                transaction_id,
                action_type,
                status,
                expected_recovery,
                actual_recovery,
                razorpay_order_id,
                executed_at
            )
            VALUES (
                :transaction_id,
                :action_type,
                :status,
                :expected_recovery,
                :actual_recovery,
                :razorpay_order_id,
                :executed_at
            )
        """)


        db.execute(
            recovery_query,
            {
                "transaction_id":
                    transaction_uuid,

                "action_type":
                    strategy,

                "status":
                    (
                        "EXECUTING"
                        if result["status"] == "ORDER_CREATED"
                        else result["status"]
                    ),

                "expected_recovery":
                    result.get(
                        "expected_recovery",
                        result["amount"]
                    ),

                "actual_recovery":
                     result["recovered_amount"],

                "razorpay_order_id":
                    result.get("razorpay_order_id"),

                "executed_at":
                    datetime.now()
            }
        )


        # =================================================
        # 2. INSERT AUDIT LOG
        # =================================================

        audit_query = text("""
            INSERT INTO audit_logs (
                merchant_id,
                transaction_id,
                event_type,
                actor,
                details
            )
            VALUES (
                :merchant_id,
                :transaction_id,
                :event_type,
                :actor,
                CAST(:details AS jsonb)
            )
        """)


        audit_details = {

            "execution_id":
                result["execution_id"],

            "strategy":
                strategy,

            "amount":
                result["amount"],

            "policy_decision":
                result["policy_decision"],

            "status":
                result["status"],

            "message":
                result["message"],

            "razorpay_order_id":
                result.get(
                    "razorpay_order_id"
                ),

            "recovered_amount":
                result["recovered_amount"]
        }


        db.execute(
            audit_query,
            {
                "merchant_id":
                    merchant_uuid,

                "transaction_id":
                    transaction_uuid,

                "event_type":
                    "RECOVERY_EXECUTED",

                "actor":
                    "recovery_executor",

                "details":
                    json.dumps(
                        audit_details
                    )
            }
        )


        # =================================================
        # 3. COMMIT
        # =================================================

        db.commit()


        print(
            "\n✓ Recovery execution persisted to PostgreSQL"
        )

        print(
            "✓ Audit log created"
        )


    except Exception as e:

        # -------------------------------------------------
        # Rollback if anything fails
        # -------------------------------------------------

        db.rollback()


        print(
            "\n✗ Database persistence failed"
        )

        print(
            f"Database error: {e}"
        )


    finally:

        db.close()


# =========================================================
# EXECUTE RECOVERY
# =========================================================

def execute_recovery(
    transaction,
    strategy
):

    # -----------------------------------------------------
    # Generate execution ID
    # -----------------------------------------------------

    execution_id = str(
        uuid.uuid4()
    )


    # -----------------------------------------------------
    # Get transaction information
    # -----------------------------------------------------

    transaction_id = transaction.get(
        "transaction_id",
        "UNKNOWN"
    )


    amount = float(
        transaction.get(
            "amount",
            0
        )
    )
        # ---------------------------------------------------------
    # IDEMPOTENCY CHECK
    # Prevent duplicate recovery actions / Razorpay orders
    # ---------------------------------------------------------

    if transaction_id:
        try:
            with SessionLocal() as db:
                existing = db.execute(
                    text("""
                        SELECT
                            id,
                            status,
                            expected_recovery,
                            actual_recovery,
                            razorpay_order_id
                        FROM recovery_actions
                        WHERE transaction_id = :transaction_id
                          AND action_type = :strategy
                          AND status IN (
                              'PENDING',
                              'APPROVED',
                              'EXECUTING',
                              'SUCCESS'
                          )
                        ORDER BY created_at DESC
                        LIMIT 1
                    """),
                    {
                        "transaction_id": transaction_id,
                        "strategy": strategy
                    }
                ).mappings().first()

                if existing:
                    exec_status = (
                        "ORDER_CREATED"
                        if existing["status"] == "EXECUTING"
                        else existing["status"]
                    )
                    return {
                        "success": True,
                        "execution_id": str(existing["id"]),
                        "transaction_id": transaction_id,
                        "strategy": strategy,
                        "amount": amount,
                        "status": exec_status,
                        "policy_decision": "ALLOW",
                        "message": (
                            "Recovery payment verified successfully. Revenue has been recovered and recorded."
                            if exec_status == "SUCCESS"
                            else "Recovery payment is ready."
                            if exec_status == "ORDER_CREATED"
                            else (
                                "Recovery already exists for this "
                                "transaction and strategy. "
                                "Duplicate Razorpay order was not created."
                            )
                        ),
                        "recovered_amount": float(
                            existing["actual_recovery"] or 0
                        ),
                        "actual_recovery": float(
                            existing["actual_recovery"] or 0
                        ),
                        "expected_recovery": float(
                            existing["expected_recovery"] or 0
                        ),
                        "razorpay_order_id": existing.get("razorpay_order_id"),
                        "idempotent": True
                    }

        except Exception as e:
            print(f"Idempotency check failed: {e}")

    # =====================================================
    # STEP 1 — POLICY VALIDATION
    # =====================================================

    policy_result = evaluate_policy(
        transaction,
        strategy
    )


    # =====================================================
    # POLICY BLOCK
    # =====================================================

    if policy_result["decision"] != "ALLOW":

        print(
            "\n✗ Recovery BLOCKED"
        )

        print(
            f"Transaction: {transaction_id}"
        )

        print(
            f"Strategy: {strategy}"
        )

        print(
            f"Reason: {policy_result['reason']}"
        )


        blocked_result = {

            "execution_id":
                execution_id,

            "transaction_id":
                transaction_id,

            "strategy":
                strategy,

            "amount":
                amount,

            "status":
                "BLOCKED",

            "policy_decision":
                "BLOCK",

            "message":
                policy_result["reason"],

            "recovered_amount":
                0.0,

            "razorpay_order_id":
                None,

            "timestamp":
                datetime.now().isoformat()
        }


        # -------------------------------------------------
        # Persist blocked decision
        # -------------------------------------------------

        persist_execution(
            transaction,
            strategy,
            blocked_result
        )


        return blocked_result


    # =====================================================
    # STEP 2 — VALIDATE STRATEGY
    # =====================================================

    if strategy not in [
        "SMART_RETRY",
        "ALTERNATIVE_PAYMENT"
    ]:

        failed_strategy_result = {

            "execution_id":
                execution_id,

            "transaction_id":
                transaction_id,

            "strategy":
                strategy,

            "amount":
                amount,

            "status":
                "FAILED",

            "policy_decision":
                "ALLOW",

            "message":
                "Unknown recovery strategy",

            "recovered_amount":
                0.0,

            "razorpay_order_id":
                None,

            "timestamp":
                datetime.now().isoformat()
        }


        persist_execution(
            transaction,
            strategy,
            failed_strategy_result
        )


        return failed_strategy_result


    # =====================================================
    # STEP 3 — EXECUTE THROUGH RAZORPAY
    # =====================================================

    print(
        f"\nExecuting recovery strategy: "
        f"{strategy}"
    )

    print(
        f"Transaction: "
        f"{transaction_id}"
    )

    print(
        f"Amount: "
        f"₹{amount:,.2f}"
    )

    print(
        "→ Creating Razorpay Test Mode order..."
    )


    try:

        # -------------------------------------------------
        # Create Razorpay Test Mode order
        # -------------------------------------------------

        razorpay_order = create_test_order(

            amount=amount,

            receipt=(
                "recovery_"
                + execution_id.replace(
                    "-",
                    ""
                )
            )
        )


        razorpay_order_id = razorpay_order["id"]


        print(
            "\n✓ Razorpay test order created"
        )

        print(
            f"Order ID: "
            f"{razorpay_order_id}"
        )

        print(
            f"Order Status: "
            f"{razorpay_order['status']}"
        )


        # =================================================
        # IMPORTANT
        # =================================================
        #
        # Creating an order does NOT mean payment succeeded.
        #
        # Therefore:
        #
        # recovered_amount = 0
        #
        # until an actual test payment is completed.
        # =================================================

        recovered_amount = 0.0

        execution_status = "ORDER_CREATED"


        # =================================================
        # BUILD SUCCESS RESULT
        # =================================================

        success_result = {

            "execution_id":
                execution_id,

            "transaction_id":
                transaction_id,

            "strategy":
                strategy,

            "amount":
                amount,
            
            "expected_recovery": float(
                transaction.get("expected_recovery", amount)
            ),
            "status":
                execution_status,

            "policy_decision":
                "ALLOW",

            "message":
                "Razorpay test order created successfully",

            "recovered_amount":
                recovered_amount,

            "razorpay_order_id":
                razorpay_order_id,

            "timestamp":
                datetime.now().isoformat()
        }


        # =================================================
        # PERSIST SUCCESSFUL EXECUTION
        # =================================================

        persist_execution(
            transaction,
            strategy,
            success_result
        )


        # =================================================
        # RETURN RESULT
        # =================================================

        return success_result


    # =====================================================
    # RAZORPAY API FAILURE
    # =====================================================

    except Exception as e:

        print(
            "\n✗ Razorpay execution failed"
        )

        print(
            f"Error: {e}"
        )


        failure_result = {

            "execution_id":
                execution_id,

            "transaction_id":
                transaction_id,

            "strategy":
                strategy,

            "amount":
                amount,

            "status":
                "FAILED",

            "policy_decision":
                "ALLOW",

            "message":
                f"Razorpay API error: {str(e)}",

            "recovered_amount":
                0.0,

            "razorpay_order_id":
                None,

            "timestamp":
                datetime.now().isoformat()
        }


        # -------------------------------------------------
        # Persist failed execution
        # -------------------------------------------------

        persist_execution(
            transaction,
            strategy,
            failure_result
        )


        return failure_result


# =========================================================
# TEST EXECUTIONS
# =========================================================

def run_tests():

    print("\n========================================")
    print("        RECOVERY EXECUTION TESTS")
    print("========================================")


    # =====================================================
    # TEST 1 — ALLOWED SMART RETRY
    # =====================================================

    transaction_1 = {

        "transaction_id":
            "EXEC-001",

        "amount":
            5000,

        "status":
            "FAILED",

        "retry_count":
            0,

        "incident_type":
            "UPI_DEGRADATION"
    }


    print("\n----------------------------------------")

    print(
        "TEST 1 — ALLOWED RECOVERY"
    )


    result = execute_recovery(

        transaction_1,

        "SMART_RETRY"
    )


    print(
        f"\nPolicy: "
        f"{result['policy_decision']}"
    )

    print(
        f"Status: "
        f"{result['status']}"
    )

    print(
        f"Message: "
        f"{result['message']}"
    )

    print(
        f"Razorpay Order: "
        f"{result['razorpay_order_id']}"
    )


    # =====================================================
    # TEST 2 — POLICY BLOCK
    # =====================================================

    transaction_2 = {

        "transaction_id":
            "EXEC-002",

        "amount":
            75000,

        "status":
            "FAILED",

        "retry_count":
            0,

        "incident_type":
            "UPI_DEGRADATION"
    }


    print("\n----------------------------------------")

    print(
        "TEST 2 — POLICY BLOCK"
    )


    result = execute_recovery(

        transaction_2,

        "SMART_RETRY"
    )


    print(
        f"\nPolicy: "
        f"{result['policy_decision']}"
    )

    print(
        f"Status: "
        f"{result['status']}"
    )

    print(
        f"Message: "
        f"{result['message']}"
    )


    # =====================================================
    # TEST 3 — ALTERNATIVE PAYMENT
    # =====================================================

    transaction_3 = {

        "transaction_id":
            "EXEC-003",

        "amount":
            15000,

        "status":
            "FAILED",

        "retry_count":
            0,

        "incident_type":
            "HIGH_VALUE_CARD_DEGRADATION"
    }


    print("\n----------------------------------------")

    print(
        "TEST 3 — ALTERNATIVE PAYMENT"
    )


    result = execute_recovery(

        transaction_3,

        "ALTERNATIVE_PAYMENT"
    )


    print(
        f"\nPolicy: "
        f"{result['policy_decision']}"
    )

    print(
        f"Status: "
        f"{result['status']}"
    )

    print(
        f"Message: "
        f"{result['message']}"
    )

    print(
        f"Razorpay Order: "
        f"{result['razorpay_order_id']}"
    )


    # =====================================================
    # TEST 4 — SUCCESSFUL TRANSACTION
    # =====================================================

    transaction_4 = {

        "transaction_id":
            "EXEC-004",

        "amount":
            10000,

        "status":
            "SUCCESS",

        "retry_count":
            0,

        "incident_type":
            "NORMAL"
    }


    print("\n----------------------------------------")

    print(
        "TEST 4 — SUCCESSFUL TRANSACTION"
    )


    result = execute_recovery(

        transaction_4,

        "ALTERNATIVE_PAYMENT"
    )


    print(
        f"\nPolicy: "
        f"{result['policy_decision']}"
    )

    print(
        f"Status: "
        f"{result['status']}"
    )

    print(
        f"Message: "
        f"{result['message']}"
    )

# =========================================================
# VERIFY RECOVERY PAYMENT
# =========================================================

def verify_recovery(transaction_id):
    """
    Verify whether the Razorpay recovery order has actually
    been paid.

    Creating an order does NOT count as recovered revenue.

    Recovery is recorded only when:
        Razorpay order status == paid
        AND amount_paid > 0
    """

    print("\n========================================")
    print("       RECOVERY VERIFICATION")
    print("========================================")

    print(f"Transaction: {transaction_id}")

    razorpay_order_id = None

    try:

        # =====================================================
        # STEP 1 — FIND ACTIVE RECOVERY ACTION
        # =====================================================

        with SessionLocal() as db:

                        recovery_record = db.execute(
                text("""
                    SELECT
                        ra.id,
                        t.merchant_id,
                        ra.transaction_id,
                        ra.action_type,
                        ra.expected_recovery,
                        ra.actual_recovery,
                        ra.status,
                        ra.razorpay_order_id
                    FROM recovery_actions ra
                    JOIN transactions t
                        ON t.id = ra.transaction_id
                    WHERE ra.transaction_id = :transaction_id
                      AND ra.status IN ('EXECUTING', 'SUCCESS')
                      AND ra.razorpay_order_id IS NOT NULL
                    ORDER BY ra.created_at DESC
                    LIMIT 1
                """),
                {
                    "transaction_id": transaction_id
                }
            ).mappings().first()


        if recovery_record["status"] == "SUCCESS":
            return {
                "success": True,
                "transaction_id": transaction_id,
                "razorpay_order_id": recovery_record["razorpay_order_id"],
                "status": "ALREADY_VERIFIED",
                "recovered_amount": float(
                    recovery_record["actual_recovery"] or 0
                ),
                "message": "Recovery payment was already verified."
            } 

        # =====================================================
        # NO ACTIVE RECOVERY FOUND
        # =====================================================

        if not recovery_record:

            print(
                "\n✗ No active recovery action found."
            )

            return {
                "success": False,
                "transaction_id": transaction_id,
                "razorpay_order_id": None,
                "status": "NOT_FOUND",
                "recovered_amount": 0.0,
                "message": (
                    "No active recovery action with a "
                    "Razorpay order was found."
                )
            }

        # =====================================================
        # GET STORED RAZORPAY ORDER
        # =====================================================

        razorpay_order_id = recovery_record["razorpay_order_id"]

        print(
            f"Razorpay Order: {razorpay_order_id}"
        )

        # =====================================================
        # STEP 2 — FETCH ORDER FROM RAZORPAY
        # =====================================================

        order = fetch_order(
            razorpay_order_id
        )

        order_status = order.get(
            "status"
        )

        amount_paid_paise = int(
            order.get(
                "amount_paid",
                0
            )
        )

        amount_paid = (
            amount_paid_paise / 100
        )

        print(
            f"Order Status: {order_status}"
        )

        print(
            f"Amount Paid: ₹{amount_paid:,.2f}"
        )

        # =====================================================
        # STEP 3 — PAYMENT NOT COMPLETED
        # =====================================================

        if (
            order_status != "paid"
            or amount_paid <= 0
        ):

            print(
                "\n→ Recovery payment not completed."
            )

            return {
                "success": False,
                "transaction_id": transaction_id,
                "razorpay_order_id": razorpay_order_id,
                "status": order_status,
                "recovered_amount": 0.0,
                "message": (
                    "Payment has not been successfully captured."
                )
            }

        # =====================================================
        # STEP 4 — MARK RECOVERY SUCCESS
        # =====================================================

        with SessionLocal() as db:

            # Re-read the recovery action to make sure it is
            # still EXECUTING before updating it.

            current_recovery = db.execute(
                text("""
                    SELECT
                        id,
                        transaction_id,
                        action_type,
                        expected_recovery,
                        actual_recovery,
                        status
                    FROM recovery_actions
                    WHERE id = :id
                      AND status = 'EXECUTING'
                    LIMIT 1
                """),
                {
                    "id": recovery_record["id"]
                }
            ).mappings().first()

            if not current_recovery:

                return {
                    "success": False,
                    "transaction_id": transaction_id,
                    "razorpay_order_id": razorpay_order_id,
                    "status": "NOT_FOUND",
                    "recovered_amount": 0.0,
                    "message": (
                        "Recovery action is no longer "
                        "in EXECUTING state."
                    )
                }

            # -------------------------------------------------
            # Update recovery action
            # -------------------------------------------------

            db.execute(
                text("""
                    UPDATE recovery_actions
                    SET
                        status = 'SUCCESS',
                        actual_recovery = :actual_recovery,
                        executed_at = NOW()
                    WHERE id = :id
                """),
                {
                    "actual_recovery": amount_paid,
                    "id": current_recovery["id"]
                }
            )

            # =================================================
            # STEP 5 — AUDIT VERIFICATION
            # =================================================

            audit_details = {
                "recovery_action_id":
                    str(current_recovery["id"]),

                "razorpay_order_id":
                    razorpay_order_id,

                "razorpay_order_status":
                    order_status,

                "amount_paid":
                    amount_paid,

                "expected_recovery":
                    float(
                        current_recovery[
                            "expected_recovery"
                        ] or 0
                    ),

                "previous_status":
                    current_recovery["status"],

                "new_status":
                    "SUCCESS"
            }

            db.execute(
                text("""
                    INSERT INTO audit_logs (
                        merchant_id,
                        transaction_id,
                        event_type,
                        actor,
                        details
                    )
                    VALUES (
                        :merchant_id,
                        :transaction_id,
                        :event_type,
                        :actor,
                        CAST(:details AS jsonb)
                    )
                """),
                {
                    "merchant_id":
                        recovery_record["merchant_id"],

                    "transaction_id":
                        current_recovery[
                            "transaction_id"
                        ],

                    "event_type":
                        "RECOVERY_VERIFIED",

                    "actor":
                        "recovery_verifier",

                    "details":
                        json.dumps(
                            audit_details
                        )
                }
            )

            db.commit()

        # =====================================================
        # SUCCESS
        # =====================================================

        print(
            "\n✓ Recovery payment verified"
        )

        print(
            f"✓ Actual recovered amount: "
            f"₹{amount_paid:,.2f}"
        )

        print(
            "✓ Recovery action marked SUCCESS"
        )

        print(
            "✓ Verification audit log created"
        )

        return {
            "success": True,
            "transaction_id": transaction_id,
            "razorpay_order_id": razorpay_order_id,
            "status": "SUCCESS",
            "recovered_amount": amount_paid,
            "message": (
                "Recovery payment verified successfully."
            )
        }

    except Exception as e:

        print(
            "\n✗ Recovery verification failed"
        )

        print(
            f"Error: {e}"
        )

        return {
            "success": False,
            "transaction_id": transaction_id,
            "razorpay_order_id": razorpay_order_id,
            "status": "FAILED",
            "recovered_amount": 0.0,
            "message": str(e)
        }
# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    run_tests()


    print("\n========================================")
    print("       RECOVERY EXECUTOR READY")
    print("========================================")


    print(
        "\nRecovery flow:"
    )

    print(
        "Transaction"
    )

    print(
        "    ↓"
    )

    print(
        "Strategy Ranking"
    )

    print(
        "    ↓"
    )

    print(
        "Policy Engine"
    )

    print(
        "    ↓"
    )

    print(
        "Recovery Executor"
    )

    print(
        "    ↓"
    )

    print(
        "Razorpay Test API"
    )

    print(
        "    ↓"
    )

    print(
        "Test Order"
    )

    print(
        "    ↓"
    )

    print(
        "PostgreSQL"
    )

    print(
        "    ↓"
    )

    print(
        "Audit Log"
    )

    print("========================================\n")