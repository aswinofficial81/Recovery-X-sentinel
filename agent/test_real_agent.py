from sqlalchemy import text

from backend.app.database import SessionLocal
from agent.recovery_agent import analyze_recovery


TRANSACTION_ID = "0abfd9eb-19f7-40ff-9267-82ee3e11ca62"


db = SessionLocal()

try:

    # ---------------------------------------------------------
    # Get real transaction from PostgreSQL
    # ---------------------------------------------------------

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
    """)

    row = db.execute(
        query,
        {"transaction_id": TRANSACTION_ID}
    ).mappings().first()

    if row is None:
        raise ValueError("Transaction not found")

    # ---------------------------------------------------------
    # Build transaction for ML
    # ---------------------------------------------------------

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
        "retry_count": max(
            0,
            row["attempt_number"] - 1
        ),
        "transaction_time": row["transaction_time"]
    }
        # ---------------------------------------------------------
    # Calculate customer history features
    # ---------------------------------------------------------

    history_query = text("""
        SELECT
            COUNT(*) AS previous_transactions,
            COUNT(*) FILTER (
                WHERE status = 'FAILED'
            ) AS previous_failures,
            COALESCE(
                COUNT(*) FILTER (
                    WHERE status = 'SUCCESS'
                )::float
                / NULLIF(COUNT(*), 0),
                0.80
            ) AS previous_success_rate
        FROM transactions
        WHERE customer_id = :customer_id
          AND transaction_time < :transaction_time
    """)

    history = db.execute(
        history_query,
        {
            "customer_id": row["customer_id"],
            "transaction_time": row["transaction_time"]
        }
    ).mappings().one()


        # ---------------------------------------------------------
    # Add ML features
    # ---------------------------------------------------------

    transaction["previous_transactions"] = int(
        history["previous_transactions"]
    )

    transaction["previous_failures"] = int(
        history["previous_failures"]
    )

    transaction["previous_success_rate"] = float(
        history["previous_success_rate"]
    )

    transaction["is_high_value"] = (
        transaction["amount"] >= 10000
    )

    transaction["transaction_velocity"] = 0

    # ---------------------------------------------------------
    # Incident classification
    # ---------------------------------------------------------

    if (
        transaction["payment_method"] == "CARD"
        and transaction["amount"] >= 10000
        and transaction["location"] == "Mumbai"
    ):
        incident_type = "HIGH_VALUE_CARD_DEGRADATION"

    elif (
        transaction["payment_method"] == "UPI"
        and transaction["location"] == "Bengaluru"
        and transaction["device"] == "ANDROID"
    ):
        incident_type = "UPI_DEGRADATION"

    else:
        incident_type = "NORMAL"
    transaction["incident_type"] = incident_type
    # ---------------------------------------------------------
    # Revenue at risk
    # ---------------------------------------------------------

    revenue_at_risk = transaction["amount"]

    # ---------------------------------------------------------
    # Run RecoverX Sentinel
    # ---------------------------------------------------------
    result = analyze_recovery(
        transaction,
        incident_type,
        revenue_at_risk=transaction["amount"],
        execute=True
    )

    # ---------------------------------------------------------
    # Display
    # ---------------------------------------------------------

    print("\n========================================")
    print("       RECOVERX SENTINEL")
    print("========================================")

    print("\nTransaction ID:")
    print(transaction["transaction_id"])

    print("\nAmount:")
    print(f"₹{transaction['amount']:,.2f}")

    print("\nPayment Method:")
    print(transaction["payment_method"])

    print("\nLocation:")
    print(transaction["location"])

    print("\nIncident:")
    print(incident_type)

    print("\n========================================")
    print("       ML STRATEGY RANKING")
    print("========================================")

    ml = result["ml_decision"]

    for item in ml["rankings"]:

        print(
            f"\n{item['rank']}. "
            f"{item['strategy']}"
        )

        print(
            f"   Recovery probability: "
            f"{item['recovery_probability'] * 100:.2f}%"
        )

        print(
            f"   Expected recovery: "
            f"₹{item['expected_recovery']:,.2f}"
        )

    print(
        "\n→ ML RECOMMENDATION:",
        ml["recommended_strategy"]
    )

    print("\n========================================")
    print("       LLM ANALYSIS")
    print("========================================")

    print("\nModel:")
    print(result["llm"]["model"])

    print(
        "\nFallback used:",
        result["llm"]["fallback_used"]
    )

    print("\nAI Analysis:")
    print(result["llm"]["response"])

    print()
    print("========================================")
    print("       POLICY DECISION")
    print("========================================")

    policy = result["policy"]

    print("Decision:")
    print(policy["decision"])

    print()
    print("Reason:")
    print(policy["reason"])


    print()
    print("========================================")
    print("       EXECUTION RESULT")
    print("========================================")

    execution = result["execution"]

    if execution:
        print("Status:")
        print(execution["status"])

        print()
        print("Strategy:")
        print(execution["strategy"])

        print()
        print("Message:")
        print(execution["message"])

        print()
        print("Recovered Amount:")
        print(
            f"₹{execution.get('recovered_amount', 0):,.2f}"
        )

        print()
        print("Idempotent:")
        print(
            execution.get("idempotent", False)
        )
    else:
        print("Execution was not performed.")

finally:

    db.close()