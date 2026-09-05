import numpy as np
import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

DATA_FILE = "data/generated_transactions.csv"


# =========================================================
# LOAD DATA
# =========================================================

def load_transaction_data():

    df = pd.read_csv(DATA_FILE)

    df["transaction_time"] = pd.to_datetime(
        df["transaction_time"]
    )

    return df


# =========================================================
# BUILD FEATURES
# =========================================================

def build_features(df):

    df = df.copy()

    # -----------------------------------------------------
    # Time features
    # -----------------------------------------------------

    # Hour is cyclical:
    # 23:00 and 00:00 should be close to each other.

    df["hour_sin"] = np.sin(
        2 * np.pi * df["hour"] / 24
    )

    df["hour_cos"] = np.cos(
        2 * np.pi * df["hour"] / 24
    )

    # -----------------------------------------------------
    # Amount feature
    # -----------------------------------------------------

    df["log_amount"] = np.log1p(
        df["amount"]
    )

    # -----------------------------------------------------
    # Customer historical behavior
    # -----------------------------------------------------

    df["failure_rate_history"] = (
        df["previous_failures"]
        /
        df["previous_transactions"].clip(
            lower=1
        )
    )

    # -----------------------------------------------------
    # Risk interaction features
    # -----------------------------------------------------

    df["high_value_retry"] = (
        df["is_high_value"].astype(int)
        *
        df["retry_count"]
    )

    df["history_failure_retry"] = (
        df["failure_rate_history"]
        *
        df["retry_count"]
    )

    return df


# =========================================================
# ENCODE CATEGORICAL FEATURES
# =========================================================

def encode_categorical_features(df):

    df = df.copy()

    categorical_columns = [
        "payment_method",
        "device",
        "location"
    ]

    df = pd.get_dummies(
        df,
        columns=categorical_columns,
        dtype=int
    )

    return df


# =========================================================
# GET MODEL FEATURES
# =========================================================

def get_feature_columns(df):

    numerical_features = [
        "log_amount",
        "hour_sin",
        "hour_cos",
        "day_of_week",
        "is_high_value",
        "is_new_customer",
        "previous_transactions",
        "previous_failures",
        "previous_success_rate",
        "retry_count",
        "transaction_velocity",
        "failure_rate_history",
        "high_value_retry",
        "history_failure_retry"
    ]

    categorical_features = [
        column
        for column in df.columns
        if column.startswith(
            "payment_method_"
        )
        or column.startswith(
            "device_"
        )
        or column.startswith(
            "location_"
        )
    ]

    return numerical_features + categorical_features


# =========================================================
# PREPARE TRAINING DATA
# =========================================================

def prepare_training_data():

    df = load_transaction_data()

    # Build engineered features
    df = build_features(df)

    # Encode categorical variables
    df = encode_categorical_features(df)

    # Select features
    feature_columns = get_feature_columns(df)

    X = df[feature_columns]

    # Target:
    #
    # SUCCESS = 0
    # FAILED  = 1

    y = (
        df["status"] == "FAILED"
    ).astype(int)

    return (
        X,
        y,
        df,
        feature_columns
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    X, y, df, feature_columns = (
        prepare_training_data()
    )

    print("\n========================================")
    print("       FEATURE ENGINEERING")
    print("========================================")

    print(
        f"\nRows: {X.shape[0]:,}"
    )

    print(
        f"Features: {X.shape[1]}"
    )

    print("\nFeature columns:")

    for feature in feature_columns:

        print(
            f"  ✓ {feature}"
        )

    print("\nFeature matrix shape:")

    print(
        f"Rows:    {X.shape[0]:,}"
    )

    print(
        f"Columns: {X.shape[1]}"
    )

    print("\nTarget distribution:")

    print(
        y.value_counts()
        .rename(
            index={
                0: "SUCCESS",
                1: "FAILED"
            }
        )
    )

    print("\nTarget percentages:")

    print(
        (
            y.value_counts(
                normalize=True
            ) * 100
        ).rename(
            index={
                0: "SUCCESS",
                1: "FAILED"
            }
        ).round(2)
    )

    print("\n========================================")
    print("Feature engineering completed.")
    print("========================================\n")