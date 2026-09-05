import os
import sys
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
# POLICY ENGINE
# =========================================================

print("\n========================================")
print("          POLICY ENGINE")
print("========================================")


# =========================================================
# POLICY CONFIGURATION
# =========================================================

POLICIES = {

    "SMART_RETRY": {
        "max_retry_count": 2,
        "max_amount": 50000,
        "allowed_incidents": [
            "UPI_DEGRADATION",
            "EVENING_DEGRADATION",
            "NORMAL"
        ]
    },

    "ALTERNATIVE_PAYMENT": {
        "max_retry_count": 0,
        "max_amount": 200000,
        "allowed_incidents": [
            "UPI_DEGRADATION",
            "HIGH_VALUE_CARD_DEGRADATION",
            "EVENING_DEGRADATION",
            "NORMAL"
        ]
    }
}


# =========================================================
# POLICY DECISION
# =========================================================

def evaluate_policy(
    transaction,
    recommended_strategy
):

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

    retry_count = int(
        transaction.get(
            "retry_count",
            0
        )
    )

    incident_type = transaction.get(
        "incident_type",
        "NORMAL"
    )

    status = transaction.get(
        "status",
        "FAILED"
    )


    # -----------------------------------------------------
    # Basic validation
    # -----------------------------------------------------

    if status != "FAILED":

        return {
            "transaction_id": transaction_id,
            "strategy": recommended_strategy,
            "decision": "BLOCK",
            "reason": "Transaction is not failed",
            "timestamp": datetime.now().isoformat()
        }


    if recommended_strategy not in POLICIES:

        return {
            "transaction_id": transaction_id,
            "strategy": recommended_strategy,
            "decision": "BLOCK",
            "reason": "Unknown recovery strategy",
            "timestamp": datetime.now().isoformat()
        }


    policy = POLICIES[
        recommended_strategy
    ]


    # -----------------------------------------------------
    # Amount check
    # -----------------------------------------------------

    if amount > policy["max_amount"]:

        return {
            "transaction_id": transaction_id,
            "strategy": recommended_strategy,
            "decision": "BLOCK",
            "reason": (
                f"Transaction amount ₹{amount:,.2f} "
                f"exceeds policy limit of "
                f"₹{policy['max_amount']:,.2f}"
            ),
            "timestamp": datetime.now().isoformat()
        }


    # -----------------------------------------------------
    # Retry check
    # -----------------------------------------------------

    if (
        recommended_strategy == "SMART_RETRY"
        and retry_count >= policy["max_retry_count"]
    ):

        return {
            "transaction_id": transaction_id,
            "strategy": recommended_strategy,
            "decision": "BLOCK",
            "reason": (
                f"Retry limit reached "
                f"({retry_count}/{policy['max_retry_count']})"
            ),
            "timestamp": datetime.now().isoformat()
        }


    # -----------------------------------------------------
    # Incident check
    # -----------------------------------------------------

    if (
        incident_type
        not in policy["allowed_incidents"]
    ):

        return {
            "transaction_id": transaction_id,
            "strategy": recommended_strategy,
            "decision": "BLOCK",
            "reason": (
                f"Strategy {recommended_strategy} "
                f"is not allowed for incident "
                f"{incident_type}"
            ),
            "timestamp": datetime.now().isoformat()
        }


    # -----------------------------------------------------
    # ALL POLICY CHECKS PASSED
    # -----------------------------------------------------

    return {
        "transaction_id": transaction_id,
        "strategy": recommended_strategy,
        "decision": "ALLOW",
        "reason": "All policy checks passed",
        "timestamp": datetime.now().isoformat()
    }


# =========================================================
# DISPLAY POLICY
# =========================================================

def print_policy():

    print("\nConfigured recovery policies:")

    for strategy, policy in POLICIES.items():

        print("\n----------------------------------------")

        print(
            f"Strategy: {strategy}"
        )

        print(
            f"Maximum amount: "
            f"₹{policy['max_amount']:,.2f}"
        )

        print(
            f"Maximum retries: "
            f"{policy['max_retry_count']}"
        )

        print(
            "Allowed incidents:"
        )

        for incident in policy[
            "allowed_incidents"
        ]:

            print(
                f"  - {incident}"
            )


# =========================================================
# TEST CASES
# =========================================================

def run_policy_tests():

    print("\n========================================")
    print("          POLICY TESTS")
    print("========================================")


    test_transactions = [

        {
            "transaction_id": "TEST-001",
            "amount": 5000,
            "status": "FAILED",
            "retry_count": 0,
            "incident_type": "UPI_DEGRADATION"
        },

        {
            "transaction_id": "TEST-002",
            "amount": 5000,
            "status": "FAILED",
            "retry_count": 2,
            "incident_type": "UPI_DEGRADATION"
        },

        {
            "transaction_id": "TEST-003",
            "amount": 75000,
            "status": "FAILED",
            "retry_count": 0,
            "incident_type": "UPI_DEGRADATION"
        },

        {
            "transaction_id": "TEST-004",
            "amount": 25000,
            "status": "SUCCESS",
            "retry_count": 0,
            "incident_type": "NORMAL"
        },

        {
            "transaction_id": "TEST-005",
            "amount": 15000,
            "status": "FAILED",
            "retry_count": 0,
            "incident_type": "HIGH_VALUE_CARD_DEGRADATION"
        }
    ]


    strategies = [
        "SMART_RETRY",
        "ALTERNATIVE_PAYMENT"
    ]


    for transaction in test_transactions:

        print("\n----------------------------------------")

        print(
            f"Transaction: "
            f"{transaction['transaction_id']}"
        )

        print(
            f"Amount: "
            f"₹{transaction['amount']:,.2f}"
        )

        print(
            f"Incident: "
            f"{transaction['incident_type']}"
        )

        print(
            f"Retry count: "
            f"{transaction['retry_count']}"
        )


        for strategy in strategies:

            result = evaluate_policy(
                transaction,
                strategy
            )

            print(
                f"\n{strategy}"
            )

            print(
                f"Decision: "
                f"{result['decision']}"
            )

            print(
                f"Reason: "
                f"{result['reason']}"
            )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print_policy()

    run_policy_tests()

    print("\n========================================")
    print("       POLICY ENGINE READY")
    print("========================================")

    print(
        "\nThe policy engine can now validate "
        "ML-generated recovery strategies "
        "before execution."
    )

    print("========================================\n")