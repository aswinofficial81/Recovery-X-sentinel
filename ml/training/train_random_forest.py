import os
import sys

import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
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
    "random_forest.joblib"
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
# TIME-BASED ORDERING
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
# TRAIN / VALIDATION / TEST
# =========================================================

n = len(df)

train_end = int(n * 0.70)

validation_end = int(n * 0.85)


X_train = X.iloc[:train_end]
y_train = y.iloc[:train_end]

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

    max_depth=12,

    min_samples_leaf=10,

    class_weight="balanced",

    random_state=42,

    n_jobs=-1
)


# =========================================================
# TRAIN
# =========================================================

print("\n========================================")
print("       TRAINING RANDOM FOREST")
print("========================================")

model.fit(
    X_train,
    y_train
)

print(
    "✓ Random Forest training completed"
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
# FINAL TEST
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
# FEATURE IMPORTANCE
# =========================================================

print("\n========================================")
print("       TOP FEATURE IMPORTANCE")
print("========================================")

feature_importance = sorted(
    zip(
        feature_columns,
        model.feature_importances_
    ),
    key=lambda x: x[1],
    reverse=True
)

for feature, importance in feature_importance[:15]:

    print(
        f"{feature:30s} "
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