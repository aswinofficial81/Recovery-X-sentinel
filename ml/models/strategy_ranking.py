import os
import sys
import joblib
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
# FILES
# =========================================================

DATA_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "recovery_experiments.csv"
)

MODEL_FILE = os.path.join(
    PROJECT_ROOT,
    "ml",
    "models",
    "recovery_prediction.joblib"
)


# =========================================================
# CONFIGURATION
# =========================================================

STRATEGIES = [
    "SMART_RETRY",
    "ALTERNATIVE_PAYMENT"
]


# =========================================================
# LOAD MODEL
# =========================================================

print("\n========================================")
print("       STRATEGY RANKING ENGINE")
print("========================================")

print("\nLoading recovery prediction model...")

package = joblib.load(
    MODEL_FILE
)

model = package["model"]
preprocessor = package["preprocessor"]
features = package["features"]

print("✓ Recovery model loaded")


# =========================================================
# LOAD DATA
# =========================================================

print("\nLoading recovery experiment data...")

df = pd.read_csv(
    DATA_FILE
)

# Missing incident labels
df["incident_type"] = df[
    "incident_type"
].fillna("NORMAL")


# Convert transaction time
df["transaction_time"] = pd.to_datetime(
    df["transaction_time"]
)


# Time features
df["hour"] = (
    df["transaction_time"].dt.hour
)

df["day_of_week"] = (
    df["transaction_time"].dt.dayofweek
)


print(
    f"Total experiment rows: {len(df):,}"
)


# =========================================================
# SELECT FAILED TRANSACTIONS
# =========================================================

failed_transactions = df[
    df["strategy"] != "NO_ACTION"
].copy()


# Make sure each transaction appears once
failed_transactions = (
    failed_transactions
    .drop_duplicates(
        subset=["transaction_id"]
    )
    .reset_index(drop=True)
)


print(
    f"Unique failed transactions: "
    f"{len(failed_transactions):,}"
)


# =========================================================
# DATA PREPARATION
# =========================================================

def prepare_transactions(
    transactions,
    strategies
):
    """
    Create one large DataFrame containing
    every transaction × every strategy.

    Example:

    Transaction 1 → SMART_RETRY
    Transaction 1 → ALTERNATIVE_PAYMENT
    Transaction 2 → SMART_RETRY
    Transaction 2 → ALTERNATIVE_PAYMENT
    ...
    """

    rows = []

    for strategy in strategies:

        strategy_df = transactions.copy()

        strategy_df["strategy"] = strategy

        rows.append(
            strategy_df
        )


    combined = pd.concat(
        rows,
        ignore_index=True
    )

        # ---------------------------------------------
    # Time features
    # ---------------------------------------------

    combined["transaction_time"] = pd.to_datetime(
        combined["transaction_time"]
    )

    combined["hour"] = (
        combined["transaction_time"].dt.hour
    )

    combined["day_of_week"] = (
        combined["transaction_time"].dt.dayofweek
    )


    # ---------------------------------------------
    # Missing value handling
    # ---------------------------------------------

    combined["incident_type"] = (
        combined["incident_type"]
        .fillna("NORMAL")
    )

    combined["previous_transactions"] = (
        combined["previous_transactions"]
        .fillna(0)
    )

    combined["previous_failures"] = (
        combined["previous_failures"]
        .fillna(0)
    )

    combined["previous_success_rate"] = (
        combined["previous_success_rate"]
        .fillna(0.80)
    )

    combined["retry_count"] = (
        combined["retry_count"]
        .fillna(0)
    )

    if "is_high_value" not in combined.columns:
        combined["is_high_value"] = combined["amount"] >= 10000
    else:
        combined["is_high_value"] = (
            combined["is_high_value"]
            .fillna(combined["amount"] >= 10000)
        )

    if "transaction_velocity" not in combined.columns:
        combined["transaction_velocity"] = 0
    else:
        combined["transaction_velocity"] = (
            combined["transaction_velocity"]
            .fillna(0)
        )


    return combined


# =========================================================
# BATCH PREDICTION
# =========================================================

def batch_predict(
    transactions,
    strategies
):
    """
    Predict recovery probability for all
    transaction × strategy combinations at once.
    """

    print("\nPreparing batch predictions...")

    combined = prepare_transactions(
        transactions,
        strategies
    )


    print(
        f"Total strategy evaluations: "
        f"{len(combined):,}"
    )


    # ---------------------------------------------
    # Keep only features used during training
    # ---------------------------------------------

    input_df = combined[
        features
    ].copy()


    print(
        "Applying feature preprocessing..."
    )


    # ---------------------------------------------
    # Transform everything at once
    # ---------------------------------------------

    processed = preprocessor.transform(
        input_df
    )


    print(
        "Running batch model prediction..."
    )


    # ---------------------------------------------
    # Predict recovery probability
    # ---------------------------------------------

    probabilities = model.predict_proba(
        processed
    )[:, 1]


    combined[
        "recovery_probability"
    ] = probabilities


    # ---------------------------------------------
    # Expected monetary recovery
    # ---------------------------------------------

    combined[
        "amount"
    ] = combined[
        "amount"
    ].astype(float)


    combined[
        "expected_recovery"
    ] = (
        combined[
            "recovery_probability"
        ]
        * combined["amount"]
    )


    return combined


# =========================================================
# RANK STRATEGIES FOR ONE TRANSACTION
# =========================================================

def rank_strategies(
    transaction
):
    """
    Rank the available strategies for a
    single transaction.

    This function is mainly used for
    demonstration/sample output.
    """

    transaction_df = pd.DataFrame(
        [transaction]
    )


    predictions = batch_predict(
        transaction_df,
        STRATEGIES
    )


    predictions = predictions.sort_values(
        "expected_recovery",
        ascending=False
    ).reset_index(
        drop=True
    )


    results = []


    for index, (_, row) in enumerate(
        predictions.iterrows(),
        start=1
    ):

        results.append({

            "rank":
                index,

            "strategy":
                row["strategy"],

            "recovery_probability":
                float(
                    row[
                        "recovery_probability"
                    ]
                ),

            "transaction_amount":
                float(
                    row["amount"]
                ),

            "expected_recovery":
                float(
                    row["expected_recovery"]
                )
        })


    return results

if __name__ == "__main__":
    # =========================================================
    # SAMPLE STRATEGY EVALUATION
    # =========================================================

    print("\n========================================")
    print("       STRATEGY EVALUATION")
    print("========================================")


    # Select 10 representative failed transactions
    samples = (
        failed_transactions
        .head(10)
    )


    for index, (_, transaction) in enumerate(
        samples.iterrows(),
        start=1
    ):

        print("\n----------------------------------------")

        print(
            f"Transaction #{index}"
        )

        print(
            f"Amount: ₹"
            f"{transaction['amount']:,.2f}"
        )

        print(
            f"Payment method: "
            f"{transaction['payment_method']}"
        )

        print(
            f"Incident: "
            f"{transaction['incident_type']}"
        )


        rankings = rank_strategies(
            transaction
        )


        print("\nStrategy ranking:")


        for result in rankings:

            print(
                f"{result['rank']}. "
                f"{result['strategy']}"
            )

            print(
                f"   Recovery probability: "
                f"{result['recovery_probability'] * 100:.2f}%"
            )

            print(
                f"   Expected recovery: "
                f"₹{result['expected_recovery']:,.2f}"
            )


        best = rankings[0]


        print(
            f"\n→ RECOMMENDED STRATEGY: "
            f"{best['strategy']}"
        )


    # =========================================================
    # BATCH STRATEGY PERFORMANCE
    # =========================================================

    print("\n========================================")
    print("       STRATEGY PERFORMANCE")
    print("========================================")


    print(
        "\nRunning batch strategy evaluation..."
    )


    # ---------------------------------------------------------
    # ONE BATCH PREDICTION
    # ---------------------------------------------------------

    results_df = batch_predict(
        failed_transactions,
        STRATEGIES
    )


    print(
        "\n✓ Batch prediction completed"
    )


    # =========================================================
    # OVERALL STRATEGY SUMMARY
    # =========================================================

    summary = (
        results_df
        .groupby(
            "strategy"
        )
        .agg(

            transactions=(
                "strategy",
                "count"
            ),

            avg_recovery_probability=(
                "recovery_probability",
                "mean"
            ),

            total_expected_recovery=(
                "expected_recovery",
                "sum"
            )
        )
    )


    # Convert probability to percentage
    summary[
        "avg_recovery_probability"
    ] *= 100


    print("\nOverall strategy performance:")

    print(
        summary.round(2)
    )


    # =========================================================
    # INCIDENT × STRATEGY
    # =========================================================

    print("\n========================================")
    print("      INCIDENT × STRATEGY")
    print("========================================")


    incident_summary = (
        results_df
        .groupby(
            [
                "incident_type",
                "strategy"
            ]
        )
        .agg(

            transactions=(
                "strategy",
                "count"
            ),

            avg_recovery_probability=(
                "recovery_probability",
                "mean"
            ),

            total_expected_recovery=(
                "expected_recovery",
                "sum"
            )
        )
    )


    incident_summary[
        "avg_recovery_probability"
    ] *= 100


    print(
        incident_summary.round(2)
    )


    # =========================================================
    # BEST STRATEGY BY INCIDENT
    # =========================================================

    print("\n========================================")
    print("      BEST STRATEGY BY INCIDENT")
    print("========================================")


    best_by_incident = (
        incident_summary
        .reset_index()
        .sort_values(
            [
                "incident_type",
                "avg_recovery_probability"
            ],
            ascending=[
                True,
                False
            ]
        )
        .groupby(
            "incident_type"
        )
        .first()
    )


    for incident, row in (
        best_by_incident.iterrows()
    ):

        print(
            f"\n{incident}"
        )

        print(
            f"  Recommended strategy: "
            f"{row['strategy']}"
        )

        print(
            f"  Recovery probability: "
            f"{row['avg_recovery_probability']:.2f}%"
        )

        print(
            f"  Expected recovery: "
            f"₹{row['total_expected_recovery']:,.2f}"
        )


    # =========================================================
    # STRATEGY WIN DISTRIBUTION
    # =========================================================

    print("\n========================================")
    print("      STRATEGY SELECTION DISTRIBUTION")
    print("========================================")


    # ---------------------------------------------------------
    # Find the strategy with the highest expected recovery
    # for every transaction.
    # ---------------------------------------------------------

    best_strategy_per_transaction = (
        results_df
        .sort_values(
            "expected_recovery",
            ascending=False
        )
        .drop_duplicates(
            subset=[
                "transaction_id"
            ]
        )
    )


    strategy_wins = (
        best_strategy_per_transaction[
            "strategy"
        ]
        .value_counts()
    )


    print(
        strategy_wins
    )


    # =========================================================
    # EXPECTED RECOVERY SUMMARY
    # =========================================================

    total_expected_recovery = (
        results_df[
            "expected_recovery"
        ].sum()
    )


    print("\n========================================")
    print("      EXPECTED RECOVERY SUMMARY")
    print("========================================")


    print(
        f"\nTotal expected recovery "
        f"across evaluated strategies: "
        f"₹{total_expected_recovery:,.2f}"
    )


    # =========================================================
    # FINAL
    # =========================================================

    print("\n========================================")
    print("     STRATEGY RANKING READY")
    print("========================================")

    print(
        "\nThe engine can now select the recovery"
        "\nstrategy with the highest expected recovery."
    )

    print(
        "\nAvailable strategies:"
    )

    print(
        "  1. SMART_RETRY"
    )

    print(
        "  2. ALTERNATIVE_PAYMENT"
    )

    print(
        "\nPipeline:"
    )

    print(
        "  Transaction"
        " → Incident"
        " → Recovery Probability"
    )

    print(
        "  → Strategy Ranking"
        " → Best Recovery Action"
    )

    print(
        "\nThe selected strategy can now be passed"
        "\nto the policy engine and recovery executor."
    )

    print("========================================\n")