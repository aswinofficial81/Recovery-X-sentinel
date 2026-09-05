import pandas as pd

from agent.recovery_agent import analyze_recovery


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
# For this test, use the transaction amount as the
# revenue-at-risk value.
#
# Later this will come from our revenue-at-risk engine.
# ---------------------------------------------------------

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