import os
import sys
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent.recovery_agent import analyze_recovery
from ml.models.revenue_risk import get_incident_revenue_risk


# ---------------------------------------------------------
# Load an actual transaction from the recovery dataset
# ---------------------------------------------------------

DATA_FILE = "data/recovery_experiments.csv"

df = pd.read_csv(DATA_FILE)

# Keep one transaction that has a recovery strategy
df = df[df["strategy"] != "NO_ACTION"].copy()

transaction = (
    df.drop_duplicates(subset=["transaction_id"])
      .iloc[0]
      .to_dict()
)


# ---------------------------------------------------------
# Get incident information
# ---------------------------------------------------------

incident_type = transaction.get("incident_type")

if pd.isna(incident_type):
    incident_type = "NORMAL"

amount = float(
    transaction["amount"]
)


# ---------------------------------------------------------
# Dynamic revenue at risk from revenue risk engine
# ---------------------------------------------------------

risk_data = get_incident_revenue_risk(incident_type)
if risk_data and risk_data.get("revenue_at_risk") is not None:
    revenue_at_risk = float(risk_data["revenue_at_risk"])
else:
    revenue_at_risk = amount


# ---------------------------------------------------------
# Run RecoverX Sentinel
# ---------------------------------------------------------

result = analyze_recovery(
    transaction=transaction,
    incident_type=incident_type,
    revenue_at_risk=revenue_at_risk
)


# ---------------------------------------------------------
# Display results
# ---------------------------------------------------------

print("\n========================================")
print("        RECOVERX SENTINEL")
print("========================================")

print("\nTransaction:")
print(transaction["transaction_id"])

print("\nAmount:")
print(f"₹{amount:,.2f}")

print("\nIncident:")
print(incident_type)


print("\n========================================")
print("        ML STRATEGY RANKING")
print("========================================")

ml_decision = result["ml_decision"]

for ranking in ml_decision["rankings"]:

    print(
        f"\n{ranking['rank']}. "
        f"{ranking['strategy']}"
    )

    print(
        f"   Recovery probability: "
        f"{ranking['recovery_probability'] * 100:.2f}%"
    )

    print(
        f"   Expected recovery: "
        f"₹{ranking['expected_recovery']:,.2f}"
    )


print(
    "\n→ ML RECOMMENDATION: "
    f"{ml_decision['recommended_strategy']}"
)


print("\n========================================")
print("        LLM ANALYSIS")
print("========================================")

print(
    "\nModel:",
    result["llm"]["model"]
)

print(
    "Fallback used:",
    result["llm"]["fallback_used"]
)

print("\nAI Analysis:")
print(result["llm"]["response"])

print("\n========================================")