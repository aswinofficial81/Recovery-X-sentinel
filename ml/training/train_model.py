import os
import sys

import joblib
import pandas as pd

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


# =========================================================
# ALLOW IMPORT FROM PROJECT ROOT
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../.."
    )
)

sys.path.insert(
    0,
    PROJECT_ROOT
)


from ml.features.feature_engineering import (
    prepare_training_data
)


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_DIR = os.path.join(
    PROJECT_ROOT,
    "ml",
    "models"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "logistic_regression.joblib"
)


# =========================================================
# LOAD DATA
# =========================================================

print("\n========================================")
print("       LOADING ML DATA")
print("========================================")

X, y, df, feature_columns = (
    prepare_training_data()
)

print(
    f"\nTotal samples: {len(X):,}"
)

print(
    f"Total features: {len(feature_columns)}"
)


# =========================================================
# SORT BY TIME
# =========================================================
#
# IMPORTANT:
#
# We don't randomly split financial transaction data.
#
# We simulate the real-world situation:
#
# Past → Training
# Recent → Validation
# Future → Test
#
# This prevents future information leaking into training.
# =========================================================

df = df.sort_values(
    "transaction_time"
)

X = X.loc[df.index]

y = y.loc[df.index]

df = df.reset_index(drop=True)
X = X.reset_index(drop=True)
y = y.reset_index(drop=True)


# =========================================================
# TIME-BASED SPLIT
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
print("       TIME-BASED DATA SPLIT")
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
    "Training:",
    df.iloc[0]["transaction_time"],
    "→",
    df.iloc[train_end - 1]["transaction_time"]
)

print(
    "Validation:",
    df.iloc[train_end]["transaction_time"],
    "→",
    df.iloc[validation_end - 1]["transaction_time"]
)

print(
    "Test:",
    df.iloc[validation_end]["transaction_time"],
    "→",
    df.iloc[-1]["transaction_time"]
)


# =========================================================
# MODEL
# =========================================================

model = Pipeline(
    steps=[

        (
            "scaler",
            StandardScaler()
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=42
            )
        )
    ]
)


# =========================================================
# TRAIN
# =========================================================

print("\n========================================")
print("       TRAINING MODEL")
print("========================================")

print(
    "\nTraining Logistic Regression..."
)

model.fit(
    X_train,
    y_train
)

print(
    "✓ Training completed"
)


# =========================================================
# VALIDATION
# =========================================================

validation_predictions = (
    model.predict(
        X_validation
    )
)

validation_probabilities = (
    model.predict_proba(
        X_validation
    )[:, 1]
)


validation_auc = (
    roc_auc_score(
        y_validation,
        validation_probabilities
    )
)


print("\n========================================")
print("       VALIDATION RESULTS")
print("========================================")

print(
    f"\nROC-AUC: "
    f"{validation_auc:.4f}"
)

print("\nClassification report:")

print(
    classification_report(
        y_validation,
        validation_predictions,
        target_names=[
            "SUCCESS",
            "FAILED"
        ]
    )
)


# =========================================================
# FINAL TEST EVALUATION
# =========================================================

test_predictions = (
    model.predict(
        X_test
    )
)

test_probabilities = (
    model.predict_proba(
        X_test
    )[:, 1]
)


test_auc = (
    roc_auc_score(
        y_test,
        test_probabilities
    )
)


print("\n========================================")
print("       FINAL TEST RESULTS")
print("========================================")

print(
    f"\nROC-AUC: "
    f"{test_auc:.4f}"
)

print("\nClassification report:")

print(
    classification_report(
        y_test,
        test_predictions,
        target_names=[
            "SUCCESS",
            "FAILED"
        ]
    )
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

cm = confusion_matrix(
    y_test,
    test_predictions
)


print("\nConfusion matrix:")

print(cm)


# =========================================================
# SAVE MODEL
# =========================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

joblib.dump(
    {
        "model": model,
        "features": feature_columns
    },
    MODEL_PATH
)


print("\n========================================")
print("       MODEL SAVED")
print("========================================")

print(
    f"\nModel path:"
)

print(
    MODEL_PATH
)

print("\n========================================\n")