import os
import sys
import joblib
import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix
)


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
    "recovery_experiments.csv"
)

MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "ml",
    "models"
)

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "recovery_prediction.joblib"
)


# =========================================================
# LOAD DATA
# =========================================================

print("\n========================================")
print("     RECOVERY PREDICTION MODEL")
print("========================================")

print("\nLoading recovery experiment data...")

df = pd.read_csv(DATA_FILE)

df["transaction_time"] = pd.to_datetime(
    df["transaction_time"]
)

print(
    f"Total experiment samples: {len(df):,}"
)


# =========================================================
# SORT BY TIME
# =========================================================

df = df.sort_values(
    "transaction_time"
).reset_index(drop=True)


# =========================================================
# CREATE TIME FEATURES
# =========================================================

df["hour"] = (
    df["transaction_time"].dt.hour
)

df["day_of_week"] = (
    df["transaction_time"].dt.dayofweek
)


# =========================================================
# TARGET
# =========================================================

TARGET = "recovery_success"


# =========================================================
# FEATURES
# =========================================================

FEATURES = [

    # Transaction characteristics
    "amount",

    # Payment context
    "payment_method",
    "device",
    "location",

    # Incident
    "incident_type",

    # Customer history
    "previous_transactions",
    "previous_failures",
    "previous_success_rate",

    # Recovery context
    "retry_count",
    "is_high_value",
    "transaction_velocity",

    # Time
    "hour",
    "day_of_week",

    # Strategy
    "strategy"
]


X = df[FEATURES].copy()

y = df[TARGET].astype(int)


# =========================================================
# TIME-BASED SPLIT
# =========================================================
#
# 70% Training
# 15% Validation
# 15% Test
#
# We do NOT randomly shuffle before splitting.
# This prevents future information leaking into training.
# =========================================================

n = len(df)

train_end = int(
    n * 0.70
)

validation_end = int(
    n * 0.85
)


X_train = X.iloc[
    :train_end
]

y_train = y.iloc[
    :train_end
]


X_validation = X.iloc[
    train_end:validation_end
]

y_validation = y.iloc[
    train_end:validation_end
]


X_test = X.iloc[
    validation_end:
]

y_test = y.iloc[
    validation_end:
]


print("\n========================================")
print("        TIME-BASED DATA SPLIT")
print("========================================")

print(
    f"\nTraining:   {len(X_train):,}"
)

print(
    f"Validation: {len(X_validation):,}"
)

print(
    f"Test:       {len(X_test):,}"
)


print("\nTime ranges:")

print(
    f"Training: "
    f"{df['transaction_time'].iloc[0]} "
    f"→ "
    f"{df['transaction_time'].iloc[train_end - 1]}"
)

print(
    f"Validation: "
    f"{df['transaction_time'].iloc[train_end]} "
    f"→ "
    f"{df['transaction_time'].iloc[validation_end - 1]}"
)

print(
    f"Test: "
    f"{df['transaction_time'].iloc[validation_end]} "
    f"→ "
    f"{df['transaction_time'].iloc[-1]}"
)


# =========================================================
# FEATURE TYPES
# =========================================================

categorical_features = [
    "payment_method",
    "device",
    "location",
    "incident_type",
    "strategy"
]


numeric_features = [
    "amount",
    "previous_transactions",
    "previous_failures",
    "previous_success_rate",
    "retry_count",
    "is_high_value",
    "transaction_velocity",
    "hour",
    "day_of_week"
]


# =========================================================
# PREPROCESSING
# =========================================================

preprocessor = ColumnTransformer(

    transformers=[

        (
            "categorical",

            OneHotEncoder(
                handle_unknown="ignore"
            ),

            categorical_features
        ),

        (
            "numeric",

            "passthrough",

            numeric_features
        )
    ]
)


# =========================================================
# TRANSFORM DATA
# =========================================================

print("\nPreparing features...")

X_train_processed = (
    preprocessor.fit_transform(
        X_train
    )
)

X_validation_processed = (
    preprocessor.transform(
        X_validation
    )
)

X_test_processed = (
    preprocessor.transform(
        X_test
    )
)


print(
    "Processed training shape:",
    X_train_processed.shape
)


# =========================================================
# TRAIN RANDOM FOREST
# =========================================================

print("\n========================================")
print("      TRAINING RECOVERY MODEL")
print("========================================")

print(
    "\nTraining Random Forest..."
)


model = RandomForestClassifier(

    n_estimators=300,

    max_depth=12,

    min_samples_leaf=5,

    class_weight="balanced",

    random_state=42,

    n_jobs=-1
)


model.fit(
    X_train_processed,
    y_train
)


print(
    "✓ Training completed"
)


# =========================================================
# HELPER FUNCTION
# =========================================================

def evaluate_model(
    model,
    X_data,
    y_data,
    name
):

    probabilities = (
        model.predict_proba(
            X_data
        )[:, 1]
    )

    predictions = (
        probabilities >= 0.50
    ).astype(int)


    accuracy = accuracy_score(
        y_data,
        predictions
    )

    precision = precision_score(
        y_data,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_data,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_data,
        predictions,
        zero_division=0
    )

    auc = roc_auc_score(
        y_data,
        probabilities
    )


    print("\n========================================")
    print(
        f"       {name.upper()} RESULTS"
    )
    print("========================================")

    print(
        f"\nAccuracy:  {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall:    {recall:.4f}"
    )

    print(
        f"F1 Score:  {f1:.4f}"
    )

    print(
        f"ROC-AUC:   {auc:.4f}"
    )


    print("\nClassification report:")

    print(
        classification_report(
            y_data,
            predictions,
            target_names=[
                "NO_RECOVERY",
                "RECOVERED"
            ],
            zero_division=0
        )
    )


    return {

        "accuracy": accuracy,

        "precision": precision,

        "recall": recall,

        "f1": f1,

        "roc_auc": auc,

        "probabilities": probabilities,

        "predictions": predictions
    }


# =========================================================
# VALIDATION
# =========================================================

validation_results = evaluate_model(

    model,

    X_validation_processed,

    y_validation,

    "Validation"
)


# =========================================================
# FINAL TEST
# =========================================================

test_results = evaluate_model(

    model,

    X_test_processed,

    y_test,

    "Final Test"
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

print("\n========================================")
print("        CONFUSION MATRIX")
print("========================================")

cm = confusion_matrix(

    y_test,

    test_results["predictions"]
)

print(cm)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

print("\n========================================")
print("       TOP RECOVERY FEATURES")
print("========================================")


feature_names = (
    preprocessor
    .get_feature_names_out()
)


importances = (
    model.feature_importances_
)


importance_df = pd.DataFrame({

    "feature":
        feature_names,

    "importance":
        importances

})


importance_df = (
    importance_df
    .sort_values(
        "importance",
        ascending=False
    )
)


print(
    importance_df
    .head(20)
    .to_string(
        index=False
    )
)


# =========================================================
# SAVE MODEL + PREPROCESSOR
# =========================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)


model_package = {

    "model": model,

    "preprocessor": preprocessor,

    "features": FEATURES,

    "categorical_features":
        categorical_features,

    "numeric_features":
        numeric_features,

    "validation_metrics": {
        "accuracy":
            validation_results["accuracy"],

        "precision":
            validation_results["precision"],

        "recall":
            validation_results["recall"],

        "f1":
            validation_results["f1"],

        "roc_auc":
            validation_results["roc_auc"]
    },

    "test_metrics": {
        "accuracy":
            test_results["accuracy"],

        "precision":
            test_results["precision"],

        "recall":
            test_results["recall"],

        "f1":
            test_results["f1"],

        "roc_auc":
            test_results["roc_auc"]
    }
}


joblib.dump(
    model_package,
    MODEL_FILE
)


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print("      RECOVERY MODEL SAVED")
print("========================================")

print(
    f"\nModel path:\n{MODEL_FILE}"
)

print("\n========================================")
print(
    "Recovery prediction training completed."
)
print("========================================\n")