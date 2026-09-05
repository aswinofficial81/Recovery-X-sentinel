import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

TRANSACTIONS_FILE = "data/generated_transactions.csv"
CUSTOMERS_FILE = "data/generated_customers.csv"


# =========================================================
# LOAD DATA
# =========================================================

transactions = pd.read_csv(
    TRANSACTIONS_FILE
)

customers = pd.read_csv(
    CUSTOMERS_FILE
)


print("\n========================================")
print("       DATASET QUALITY VALIDATION")
print("========================================")


# =========================================================
# 1. ROW COUNTS
# =========================================================

print("\n[1] Row counts")

print(
    f"Customers: {len(customers):,}"
)

print(
    f"Transactions: {len(transactions):,}"
)

assert len(customers) == 5000, (
    "Customer count is not 5,000"
)

assert len(transactions) == 50000, (
    "Transaction count is not 50,000"
)

print("✓ Row counts valid")


# =========================================================
# 2. UNIQUE IDs
# =========================================================

print("\n[2] ID uniqueness")

duplicate_transactions = (
    transactions["transaction_id"]
    .duplicated()
    .sum()
)

duplicate_customers = (
    customers["customer_id"]
    .duplicated()
    .sum()
)

print(
    f"Duplicate transaction IDs: "
    f"{duplicate_transactions}"
)

print(
    f"Duplicate customer IDs: "
    f"{duplicate_customers}"
)

assert duplicate_transactions == 0
assert duplicate_customers == 0

print("✓ IDs are unique")


# =========================================================
# 3. REQUIRED COLUMNS
# =========================================================

print("\n[3] Required columns")

required_columns = [
    "transaction_id",
    "merchant_id",
    "customer_id",
    "amount",
    "currency",
    "payment_method",
    "status",
    "device",
    "location",
    "transaction_time",
    "attempt_number",
    "hour",
    "day_of_week",
    "is_high_value",
    "is_new_customer",
    "previous_transactions",
    "previous_failures",
    "previous_success_rate",
    "retry_count",
    "transaction_velocity",
    "is_incident",
    "incident_type"
]

missing_columns = [
    column
    for column in required_columns
    if column not in transactions.columns
]

print(
    f"Missing columns: {missing_columns}"
)

assert len(missing_columns) == 0

print("✓ Required columns present")


# =========================================================
# 4. NULL CHECK
# =========================================================

print("\n[4] Missing values")

critical_columns = [
    "transaction_id",
    "merchant_id",
    "customer_id",
    "amount",
    "currency",
    "payment_method",
    "status",
    "device",
    "location",
    "transaction_time"
]

null_counts = (
    transactions[critical_columns]
    .isnull()
    .sum()
)

print(null_counts)

assert null_counts.sum() == 0

print("✓ No missing critical values")


# =========================================================
# 5. AMOUNT VALIDATION
# =========================================================

print("\n[5] Amount validation")

invalid_amounts = (
    (transactions["amount"] <= 0)
    |
    (transactions["amount"] > 50000)
).sum()

print(
    f"Invalid amounts: {invalid_amounts}"
)

assert invalid_amounts == 0

print("✓ Amounts are valid")


# =========================================================
# 6. STATUS VALIDATION
# =========================================================

print("\n[6] Status validation")

valid_statuses = {
    "SUCCESS",
    "FAILED"
}

invalid_statuses = set(
    transactions["status"].unique()
) - valid_statuses

print(
    f"Invalid statuses: {invalid_statuses}"
)

assert len(invalid_statuses) == 0

print("✓ Status values valid")


# =========================================================
# 7. PAYMENT METHOD VALIDATION
# =========================================================

print("\n[7] Payment method validation")

valid_methods = {
    "UPI",
    "CARD",
    "NETBANKING",
    "WALLET"
}

invalid_methods = set(
    transactions["payment_method"].unique()
) - valid_methods

print(
    f"Invalid payment methods: "
    f"{invalid_methods}"
)

assert len(invalid_methods) == 0

print("✓ Payment methods valid")


# =========================================================
# 8. DEVICE VALIDATION
# =========================================================

print("\n[8] Device validation")

valid_devices = {
    "ANDROID",
    "IOS",
    "DESKTOP"
}

invalid_devices = set(
    transactions["device"].unique()
) - valid_devices

print(
    f"Invalid devices: {invalid_devices}"
)

assert len(invalid_devices) == 0

print("✓ Devices valid")


# =========================================================
# 9. LOCATION VALIDATION
# =========================================================

print("\n[9] Location validation")

valid_locations = {
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "Chennai",
    "Hyderabad"
}

invalid_locations = set(
    transactions["location"].unique()
) - valid_locations

print(
    f"Invalid locations: {invalid_locations}"
)

assert len(invalid_locations) == 0

print("✓ Locations valid")


# =========================================================
# 10. CUSTOMER REFERENCES
# =========================================================

print("\n[10] Customer references")

customer_ids = set(
    customers["customer_id"]
)

transaction_customer_ids = set(
    transactions["customer_id"]
)

unknown_customers = (
    transaction_customer_ids
    - customer_ids
)

print(
    f"Unknown customer references: "
    f"{len(unknown_customers)}"
)

assert len(unknown_customers) == 0

print("✓ All customers referenced correctly")


# =========================================================
# 11. ML FEATURE VALIDATION
# =========================================================

print("\n[11] ML feature validation")

assert transactions["hour"].between(
    0, 23
).all()

assert transactions["day_of_week"].between(
    0, 6
).all()

assert (
    transactions["previous_transactions"]
    >= 0
).all()

assert (
    transactions["previous_failures"]
    >= 0
).all()

assert transactions[
    "previous_success_rate"
].between(0, 1).all()

assert (
    transactions["retry_count"]
    >= 0
).all()

assert (
    transactions["transaction_velocity"]
    >= 1
).all()

print("✓ ML features are within valid ranges")


# =========================================================
# 12. INCIDENT LABEL VALIDATION
# =========================================================

print("\n[12] Incident labels")

valid_incidents = {
    "UPI_DEGRADATION",
    "HIGH_VALUE_CARD_DEGRADATION",
    "EVENING_DEGRADATION"
}

incident_rows = transactions[
    transactions["is_incident"] == True
]

normal_rows = transactions[
    transactions["is_incident"] == False
]

print(
    f"Incident transactions: "
    f"{len(incident_rows):,}"
)

print(
    f"Normal transactions: "
    f"{len(normal_rows):,}"
)

invalid_incidents = set(
    incident_rows["incident_type"].dropna().unique()
) - valid_incidents

assert len(invalid_incidents) == 0

# Every incident must have a label
assert (
    incident_rows["incident_type"]
    .notnull()
    .all()
)

# Normal transactions must not have an incident label
assert (
    normal_rows["incident_type"]
    .isnull()
    .all()
)

print("✓ Incident labels are consistent")


# =========================================================
# 13. INCIDENT COUNTS
# =========================================================

print("\n[13] Incident distribution")

incident_distribution = (
    transactions["incident_type"]
    .fillna("NORMAL")
    .value_counts()
)

print(
    incident_distribution
)


# =========================================================
# 14. INCIDENT SUCCESS RATES
# =========================================================

print("\n[14] Incident success rates")

transactions["success_flag"] = (
    transactions["status"]
    == "SUCCESS"
)

success_rates = (
    transactions
    .assign(
        incident_type=
        transactions["incident_type"]
        .fillna("NORMAL")
    )
    .groupby("incident_type")[
        "success_flag"
    ]
    .mean()
    * 100
)

for incident, rate in success_rates.items():

    print(
        f"{incident}: "
        f"{rate:.2f}%"
    )


# =========================================================
# 15. FINAL SUMMARY
# =========================================================

print("\n========================================")
print("       DATASET VALIDATION PASSED")
print("========================================")

print("\n✓ 5,000 customers")
print("✓ 50,000 transactions")
print("✓ Unique transaction IDs")
print("✓ Unique customer IDs")
print("✓ No critical missing values")
print("✓ Valid transaction amounts")
print("✓ Valid categorical values")
print("✓ Valid customer references")
print("✓ Valid ML feature ranges")
print("✓ Consistent incident labels")
print("✓ Dataset is ready for PostgreSQL")
print("✓ Dataset is ready for ML pipeline")

print("\n========================================\n")