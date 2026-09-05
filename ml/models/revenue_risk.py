import os
import sys

import pandas as pd


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
# CONFIGURATION
# =========================================================

DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "generated_transactions.csv"
)


# =========================================================
# LOAD DATA
# =========================================================

def load_data():

    df = pd.read_csv(
        DATA_FILE
    )

    df["transaction_time"] = pd.to_datetime(
        df["transaction_time"]
    )

    return df


# =========================================================
# CALCULATE MERCHANT BASELINE
# =========================================================

def calculate_baseline(df):

    total_transactions = len(df)

    successful_transactions = (
        df["status"] == "SUCCESS"
    ).sum()

    baseline_success_rate = (
        successful_transactions
        / total_transactions
    )

    return baseline_success_rate


# =========================================================
# CALCULATE REVENUE RISK
# =========================================================

def calculate_revenue_risk(
    df,
    incident_type,
    baseline_success_rate
):

    incident_df = df[
        df["incident_type"] == incident_type
    ].copy()

    if len(incident_df) == 0:

        return None


    # -----------------------------------------------------
    # Transaction counts
    # -----------------------------------------------------

    transaction_count = len(
        incident_df
    )

    successful_count = (
        incident_df["status"] == "SUCCESS"
    ).sum()

    failed_count = (
        incident_df["status"] == "FAILED"
    ).sum()


    # -----------------------------------------------------
    # Actual success rate
    # -----------------------------------------------------

    actual_success_rate = (
        successful_count
        / transaction_count
    )


    # -----------------------------------------------------
    # Expected successful transactions
    #
    # If this segment behaved like the merchant baseline:
    # -----------------------------------------------------

    expected_successful_transactions = (
        transaction_count
        * baseline_success_rate
    )


    # -----------------------------------------------------
    # Lost transaction opportunities
    # -----------------------------------------------------

    lost_transactions = max(
        0,
        expected_successful_transactions
        - successful_count
    )


    # -----------------------------------------------------
    # Average transaction amount
    # -----------------------------------------------------

    average_amount = (
        incident_df["amount"].mean()
    )


    # -----------------------------------------------------
    # Expected revenue
    # -----------------------------------------------------

    expected_revenue = (
        expected_successful_transactions
        * average_amount
    )


    # -----------------------------------------------------
    # Actual revenue
    # -----------------------------------------------------

    actual_revenue = (
        incident_df.loc[
            incident_df["status"] == "SUCCESS",
            "amount"
        ].sum()
    )


    # -----------------------------------------------------
    # Revenue at risk
    # -----------------------------------------------------

    revenue_at_risk = max(
        0,
        expected_revenue
        - actual_revenue
    )


    # -----------------------------------------------------
    # Incident severity
    # -----------------------------------------------------

    success_rate_drop = (
        baseline_success_rate
        - actual_success_rate
    )


    if success_rate_drop >= 0.20:

        severity = "CRITICAL"

    elif success_rate_drop >= 0.10:

        severity = "HIGH"

    elif success_rate_drop >= 0.05:

        severity = "MEDIUM"

    else:

        severity = "LOW"


    # -----------------------------------------------------
    # Confidence
    #
    # Larger samples produce more reliable estimates.
    # -----------------------------------------------------

    confidence = min(
        0.99,
        0.50
        + (
            transaction_count
            / 1000
        ) * 0.49
    )


    return {

        "incident_type":
            incident_type,

        "transaction_count":
            int(transaction_count),

        "successful_transactions":
            int(successful_count),

        "failed_transactions":
            int(failed_count),

        "baseline_success_rate":
            round(
                baseline_success_rate * 100,
                2
            ),

        "actual_success_rate":
            round(
                actual_success_rate * 100,
                2
            ),

        "success_rate_drop":
            round(
                success_rate_drop * 100,
                2
            ),

        "expected_successful_transactions":
            round(
                expected_successful_transactions,
                2
            ),

        "lost_transactions":
            round(
                lost_transactions,
                2
            ),

        "average_transaction_amount":
            round(
                average_amount,
                2
            ),

        "expected_revenue":
            round(
                expected_revenue,
                2
            ),

        "actual_revenue":
            round(
                actual_revenue,
                2
            ),

        "revenue_at_risk":
            round(
                revenue_at_risk,
                2
            ),

        "severity":
            severity,

        "confidence":
            round(
                confidence,
                2
            )
    }


# =========================================================
# ANALYZE ALL INCIDENTS
# =========================================================

def analyze_all_incidents():

    df = load_data()

    baseline = calculate_baseline(
        df
    )

    incident_types = [
        "UPI_DEGRADATION",
        "HIGH_VALUE_CARD_DEGRADATION",
        "EVENING_DEGRADATION"
    ]

    results = []

    for incident_type in incident_types:

        result = calculate_revenue_risk(
            df,
            incident_type,
            baseline
        )

        if result is not None:

            results.append(
                result
            )

    return (
        baseline,
        results
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("\n========================================")
    print("       REVENUE AT RISK ENGINE")
    print("========================================")


    baseline, results = (
        analyze_all_incidents()
    )


    print(
        f"\nMerchant baseline success rate: "
        f"{baseline * 100:.2f}%"
    )


    print("\n========================================")
    print("       INCIDENT REVENUE RISK")
    print("========================================")


    total_risk = 0


    for result in results:

        print("\n----------------------------------------")

        print(
            f"Incident: "
            f"{result['incident_type']}"
        )

        print(
            f"Transactions: "
            f"{result['transaction_count']:,}"
        )

        print(
            f"Success rate: "
            f"{result['actual_success_rate']:.2f}%"
        )

        print(
            f"Baseline: "
            f"{result['baseline_success_rate']:.2f}%"
        )

        print(
            f"Success-rate drop: "
            f"{result['success_rate_drop']:.2f}%"
        )

        print(
            f"Lost transactions: "
            f"{result['lost_transactions']:.2f}"
        )

        print(
            f"Expected revenue: "
            f"₹{result['expected_revenue']:,.2f}"
        )

        print(
            f"Actual revenue: "
            f"₹{result['actual_revenue']:,.2f}"
        )

        print(
            f"Revenue at risk: "
            f"₹{result['revenue_at_risk']:,.2f}"
        )

        print(
            f"Severity: "
            f"{result['severity']}"
        )

        print(
            f"Confidence: "
            f"{result['confidence']:.2f}"
        )

        total_risk += (
            result["revenue_at_risk"]
        )


    print("\n========================================")

    print(
        f"TOTAL REVENUE AT RISK: "
        f"₹{total_risk:,.2f}"
    )

    print("========================================\n")