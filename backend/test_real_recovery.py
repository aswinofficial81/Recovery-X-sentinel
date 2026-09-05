import sys
import os


# =========================================================
# PROJECT ROOT
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

sys.path.insert(0, PROJECT_ROOT)


# =========================================================
# IMPORT DATABASE
# =========================================================

from sqlalchemy import text

from backend.app.database import SessionLocal


# =========================================================
# IMPORT RECOVERY EXECUTOR
# =========================================================

from ml.models.recovery_executor import execute_recovery


# =========================================================
# REAL TRANSACTION ID
# =========================================================

TRANSACTION_ID = (
    "da99976f-0d47-42c4-ad62-efad6621cee6"
)


# =========================================================
# LOAD TRANSACTION FROM DATABASE
# =========================================================

def load_transaction():

    db = SessionLocal()

    try:

        query = text("""
            SELECT
                id,
                merchant_id,
                amount,
                currency,
                payment_method,
                status,
                failure_reason,
                device,
                location,
                attempt_number
            FROM transactions
            WHERE id = :transaction_id
        """)

        row = db.execute(
            query,
            {
                "transaction_id":
                    TRANSACTION_ID
            }
        ).mappings().one()

        transaction = {

            "transaction_id":
                str(row["id"]),

            "merchant_id":
                str(row["merchant_id"]),

            "amount":
                float(row["amount"]),

            "currency":
                row["currency"],

            "payment_method":
                row["payment_method"],

            "status":
                row["status"],

            "failure_reason":
                row["failure_reason"],

            "device":
                row["device"],

            "location":
                row["location"],

            "retry_count":
                max(
                    0,
                    row["attempt_number"] - 1
                ),

            # This transaction matches our
            # planted high-value CARD incident pattern.
            "incident_type":
                "HIGH_VALUE_CARD_DEGRADATION"
        }

        return transaction

    finally:

        db.close()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("\n========================================")
    print("       REAL RECOVERY TEST")
    print("========================================")


    # -----------------------------------------------------
    # LOAD REAL TRANSACTION
    # -----------------------------------------------------

    transaction = load_transaction()


    print("\nTransaction loaded from PostgreSQL")

    print(
        f"Transaction ID: "
        f"{transaction['transaction_id']}"
    )

    print(
        f"Merchant ID: "
        f"{transaction['merchant_id']}"
    )

    print(
        f"Amount: "
        f"₹{transaction['amount']:,.2f}"
    )

    print(
        f"Payment Method: "
        f"{transaction['payment_method']}"
    )

    print(
        f"Status: "
        f"{transaction['status']}"
    )

    print(
        f"Device: "
        f"{transaction['device']}"
    )

    print(
        f"Location: "
        f"{transaction['location']}"
    )

    print(
        f"Incident: "
        f"{transaction['incident_type']}"
    )


    # -----------------------------------------------------
    # EXECUTE RECOVERY
    # -----------------------------------------------------

    print("\n----------------------------------------")

    print(
        "Executing ALTERNATIVE_PAYMENT..."
    )


    result = execute_recovery(

        transaction,

        "ALTERNATIVE_PAYMENT"
    )


    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    print("\n----------------------------------------")

    print("RECOVERY RESULT")

    print(
        f"Policy: "
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

    print(
        f"Recovered Amount: "
        f"₹{result['recovered_amount']:,.2f}"
    )

    print(
        f"Execution ID: "
        f"{result['execution_id']}"
    )


    print("\n========================================")
    print("       REAL RECOVERY TEST COMPLETE")
    print("========================================")