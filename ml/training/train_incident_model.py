import os
import sys

import joblib
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    f1_score
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

sys.path.insert(
    0,
    PROJECT_ROOT
)


from ml.features.feature_engineering import (
    load_transaction_data,
    build_features,
    encode_categorical_features,
    get_feature_columns
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
    "incident_detection.joblib"
)


# =========================================================
# LOAD DATA
# =========================================================

print("\n========================================")
print("     INCIDENT DETECTION MODEL")
print("========================================")

df = load_transaction_data()

print(
    f"\nTotal transactions: {len(df):,}"
)


# =========================================================
# FEATURE ENGINEERING
# =========================================================

df = build_features(df)

df = encode_categorical_features(df)


# =========================================================
# DOMAIN-SPECIFIC INTERACTION FEATURES
# =========================================================
#
# These represent combinations that are meaningful
# in payment systems.
#
# We are NOT using incident_type itself as a feature.
# Therefore there is no target leakage.
# =========================================================

df["is_upi_android"] = (
    (
        df["payment_method_UPI"] == 1
    )
    &
    (
        df["device_ANDROID"] == 1
    )
).astype(int)


df["is_bengaluru_upi"] = (
    (
        df["payment_method_UPI"] == 1
    )
    &
    (
        df["location_Bengaluru"] == 1
    )
).astype(int)


df["is_mumbai_card"] = (
    (
        df["payment_method_CARD"] == 1
    )
    &
    (
        df["location_Mumbai"] == 1
    )
).astype(int)


df["is_high_value_card"] = (
    (
        df["payment_method_CARD"] == 1
    )
    &
    (
        df["is_high_value"].astype(int) == 1
    )
).astype(int)


df["is_evening"] = (
    df["hour"].between(18, 20)
).astype(int)


df["is_upi_bengaluru_evening"] = (
    (
        df["payment_method_UPI"] == 1
    )
    &
    (
        df["location_Bengaluru"] == 1
    )
    &
    (
        df["hour"].between(20, 23)
    )
).astype(int)


# =========================================================
# FEATURE COLUMNS
# =========================================================

feature_columns = get_feature_columns(df)


interaction_features = [

    "is_upi_android",

    "is_bengaluru_upi",

    "is_mumbai_card",

    "is_high_value_card",

    "is_evening",

    "is_upi_bengaluru_evening"
]


feature_columns = (
    feature_columns
    + interaction_features
)


X = df[feature_columns]


# =========================================================
# TARGET
# =========================================================
#
# NORMAL = 0
# UPI_DEGRADATION = 1
# HIGH_VALUE_CARD_DEGRADATION = 2
# EVENING_DEGRADATION = 3
# =========================================================

df["incident_label"] = (
    df["incident_type"]
    .fillna("NORMAL")
)


label_mapping = {

    "NORMAL": 0,

    "UPI_DEGRADATION": 1,

    "HIGH_VALUE_CARD_DEGRADATION": 2,

    "EVENING_DEGRADATION": 3
}


y = df["incident_label"].map(
    label_mapping
)


# =========================================================
# VERIFY TARGET
# =========================================================

if y.isnull().any():

    raise ValueError(
        "Unknown incident type found."
    )


y = y.astype(int)


print("\nIncident distribution:")

print(
    df["incident_label"]
    .value_counts()
)


# =========================================================
# TIME-BASED SPLIT
# =========================================================

df = df.sort_values(
    "transaction_time"
)

X = X.loc[df.index]

y = y.loc[df.index]

df = df.reset_index(drop=True)

X = X.reset_index(drop=True)

y = y.reset_index(drop=True)


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


# =========================================================
# RANDOM FOREST
# =========================================================

model = RandomForestClassifier(

    n_estimators=300,

    max_depth=14,

    min_samples_leaf=5,

    class_weight="balanced",

    random_state=42,

    n_jobs=-1
)


# =========================================================
# TRAIN
# =========================================================

print("\n========================================")
print("       TRAINING INCIDENT MODEL")
print("========================================")

print(
    "\nTraining Random Forest..."
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


validation_f1 = f1_score(
    y_validation,
    validation_predictions,
    average="macro"
)


validation_accuracy = accuracy_score(
    y_validation,
    validation_predictions
)


print("\n========================================")
print("       VALIDATION RESULTS")
print("========================================")

print(
    f"\nAccuracy: "
    f"{validation_accuracy:.4f}"
)

print(
    f"Macro F1: "
    f"{validation_f1:.4f}"
)

print("\nClassification report:")

print(
    classification_report(
        y_validation,
        validation_predictions,
        labels=[0, 1, 2, 3],
        target_names=[
            "NORMAL",
            "UPI_DEGRADATION",
            "HIGH_VALUE_CARD_DEGRADATION",
            "EVENING_DEGRADATION"
        ],
        zero_division=0
    )
)


# =========================================================
# FINAL TEST
# =========================================================

test_predictions = (
    model.predict(
        X_test
    )
)


test_accuracy = accuracy_score(
    y_test,
    test_predictions
)


test_f1 = f1_score(
    y_test,
    test_predictions,
    average="macro"
)


print("\n========================================")
print("       FINAL TEST RESULTS")
print("========================================")

print(
    f"\nAccuracy: "
    f"{test_accuracy:.4f}"
)

print(
    f"Macro F1: "
    f"{test_f1:.4f}"
)

print("\nClassification report:")

print(
    classification_report(
        y_test,
        test_predictions,
        labels=[0, 1, 2, 3],
        target_names=[
            "NORMAL",
            "UPI_DEGRADATION",
            "HIGH_VALUE_CARD_DEGRADATION",
            "EVENING_DEGRADATION"
        ],
        zero_division=0
    )
)


# =========================================================
# CONFUSION MATRIX
# =========================================================

cm = confusion_matrix(
    y_test,
    test_predictions,
    labels=[0, 1, 2, 3]
)


print("\nConfusion matrix:")

print(cm)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

print("\n========================================")
print("       TOP INCIDENT FEATURES")
print("========================================")


feature_importance = sorted(
    zip(
        feature_columns,
        model.feature_importances_
    ),
    key=lambda x: x[1],
    reverse=True
)


for feature, importance in (
    feature_importance[:20]
):

    print(
        f"{feature:35s}"
        f"{importance:.4f}"
    )


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
        "features": feature_columns,
        "label_mapping": label_mapping
    },
    MODEL_PATH
)


print("\n========================================")
print("       INCIDENT MODEL SAVED")
print("========================================")

print(
    f"\nModel path:"
)

print(
    MODEL_PATH
)

print("\n========================================\n")