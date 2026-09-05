import os
import random

import numpy as np
import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

TRANSACTION_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "generated_transactions.csv"
)

OUTPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "recovery_experiments.csv"
)


random.seed(42)
np.random.seed(42)


# =========================================================
# LOAD TRANSACTIONS
# =========================================================

df = pd.read_csv(
    TRANSACTION_FILE
)

df["transaction_time"] = pd.to_datetime(
    df["transaction_time"]
)


# =========================================================
# ONLY FAILED TRANSACTIONS
# =========================================================
#
# Recovery is relevant when the original transaction
# failed.
# =========================================================

failed = df[
    df["status"] == "FAILED"
].copy()


print("\n========================================")
print("   RECOVERY EXPERIMENT GENERATION")
print("========================================")

print(
    f"\nFailed transactions: "
    f"{len(failed):,}"
)


# =========================================================
# STRATEGIES
# =========================================================

STRATEGIES = [

    "NO_ACTION",

    "SMART_RETRY",

    "ALTERNATIVE_PAYMENT"
]


# =========================================================
# RECOVERY PROBABILITY
# =========================================================

def calculate_recovery_probability(
    row,
    strategy
):

    # -----------------------------------------------------
    # No action
    # -----------------------------------------------------

    if strategy == "NO_ACTION":

        return 0.0


    # -----------------------------------------------------
    # Base probability
    # -----------------------------------------------------

    if strategy == "SMART_RETRY":

        probability = 0.30

    else:

        probability = 0.40


    # -----------------------------------------------------
    # Incident-specific behavior
    # -----------------------------------------------------

    incident = row.get(
        "incident_type",
        "NORMAL"
    )


    if incident == "UPI_DEGRADATION":

        if strategy == "SMART_RETRY":

            probability += 0.18

        elif strategy == "ALTERNATIVE_PAYMENT":

            probability += 0.08


    elif incident == "HIGH_VALUE_CARD_DEGRADATION":

        if strategy == "SMART_RETRY":

            probability += 0.05

        elif strategy == "ALTERNATIVE_PAYMENT":

            probability += 0.20


    elif incident == "EVENING_DEGRADATION":

        if strategy == "SMART_RETRY":

            probability += 0.12

        elif strategy == "ALTERNATIVE_PAYMENT":

            probability += 0.10


    # -----------------------------------------------------
    # Payment method
    # -----------------------------------------------------

    payment_method = row[
        "payment_method"
    ]


    if (
        payment_method == "UPI"
        and strategy == "SMART_RETRY"
    ):

        probability += 0.05


    if (
        payment_method == "CARD"
        and strategy == "ALTERNATIVE_PAYMENT"
    ):

        probability += 0.08


    # -----------------------------------------------------
    # Historical customer behavior
    # -----------------------------------------------------

    previous_success_rate = row.get(
        "previous_success_rate",
        0.8
    )


    if previous_success_rate >= 0.90:

        probability += 0.08

    elif previous_success_rate < 0.50:

        probability -= 0.08


    # -----------------------------------------------------
    # Previous failures
    # -----------------------------------------------------

    previous_failures = row.get(
        "previous_failures",
        0
    )


    probability -= min(
        previous_failures * 0.015,
        0.10
    )


    # -----------------------------------------------------
    # Retry count
    # -----------------------------------------------------

    retry_count = row.get(
        "retry_count",
        0
    )


    probability -= min(
        retry_count * 0.05,
        0.15
    )


    # -----------------------------------------------------
    # High-value transactions
    # -----------------------------------------------------

    is_high_value = row.get(
        "is_high_value",
        False
    )


    if bool(is_high_value):

        if strategy == "ALTERNATIVE_PAYMENT":

            probability += 0.05

        elif strategy == "SMART_RETRY":

            probability -= 0.03


    # -----------------------------------------------------
    # Clamp probability
    # -----------------------------------------------------

    return max(
        0.02,
        min(
            probability,
            0.90
        )
    )


# =========================================================
# GENERATE EXPERIMENTS
# =========================================================

experiments = []


for _, row in failed.iterrows():

    for strategy in STRATEGIES:

        recovery_probability = (
            calculate_recovery_probability(
                row,
                strategy
            )
        )


        recovery_success = (
            random.random()
            < recovery_probability
        )


        if recovery_success:

            recovered_amount = (
                row["amount"]
            )

        else:

            recovered_amount = 0.0


        experiments.append({

            "transaction_id":
                row["transaction_id"],

            "merchant_id":
                row["merchant_id"],

            "customer_id":
                row["customer_id"],

            "amount":
                row["amount"],

            "payment_method":
                row["payment_method"],

            "device":
                row["device"],

            "location":
                row["location"],

            "transaction_time":
                row["transaction_time"],

            "incident_type":
                row.get(
                    "incident_type",
                    "NORMAL"
                ),

            "previous_transactions":
                row.get(
                    "previous_transactions",
                    0
                ),

            "previous_failures":
                row.get(
                    "previous_failures",
                    0
                ),

            "previous_success_rate":
                row.get(
                    "previous_success_rate",
                    0.8
                ),

            "retry_count":
                row.get(
                    "retry_count",
                    0
                ),

            "is_high_value":
                row.get(
                    "is_high_value",
                    False
                ),

            "transaction_velocity":
                row.get(
                    "transaction_velocity",
                    0
                ),

            "strategy":
                strategy,

            "recovery_probability":
                round(
                    recovery_probability,
                    4
                ),

            "recovery_success":
                int(
                    recovery_success
                ),

            "recovered_amount":
                round(
                    recovered_amount,
                    2
                )
        })


# =========================================================
# CREATE DATAFRAME
# =========================================================

experiments_df = pd.DataFrame(
    experiments
)


# =========================================================
# SHUFFLE
# =========================================================

experiments_df = (
    experiments_df
    .sample(
        frac=1,
        random_state=42
    )
    .reset_index(drop=True)
)


# =========================================================
# SAVE
# =========================================================

experiments_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# =========================================================
# SUMMARY
# =========================================================

print("\n========================================")
print("   RECOVERY DATASET GENERATED")
print("========================================")

print(
    f"\nFailed transactions: "
    f"{len(failed):,}"
)

print(
    f"Experiment rows: "
    f"{len(experiments_df):,}"
)


print("\nStrategy distribution:")

print(
    experiments_df[
        "strategy"
    ].value_counts()
)


print("\nRecovery results:")

strategy_summary = (
    experiments_df
    .groupby("strategy")
    .agg(
        attempts=(
            "transaction_id",
            "count"
        ),
        successful_recoveries=(
            "recovery_success",
            "sum"
        ),
        recovery_rate=(
            "recovery_success",
            "mean"
        ),
        recovered_revenue=(
            "recovered_amount",
            "sum"
        )
    )
)


strategy_summary[
    "recovery_rate"
] *= 100


print(
    strategy_summary.round(2)
)


print("\nIncident × Strategy:")

incident_summary = (
    experiments_df
    .groupby(
        [
            "incident_type",
            "strategy"
        ]
    )
    .agg(
        attempts=(
            "transaction_id",
            "count"
        ),
        recovery_rate=(
            "recovery_success",
            "mean"
        ),
        recovered_revenue=(
            "recovered_amount",
            "sum"
        )
    )
)


incident_summary[
    "recovery_rate"
] *= 100


print(
    incident_summary.round(2)
)


print("\n========================================")

print(
    "Recovery experiment dataset ready."
)

print(
    f"Saved to:\n{OUTPUT_FILE}"
)

print("========================================\n")