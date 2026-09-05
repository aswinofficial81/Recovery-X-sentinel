import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker


# =========================================================
# CONFIGURATION
# =========================================================

NUM_CUSTOMERS = 5000
NUM_TRANSACTIONS = 50000

MERCHANT_ID = "demo-merchant-001"

PAYMENT_METHODS = [
    "UPI",
    "CARD",
    "NETBANKING",
    "WALLET"
]

DEVICES = [
    "ANDROID",
    "IOS",
    "DESKTOP"
]

LOCATIONS = [
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "Chennai",
    "Hyderabad"
]

fake = Faker("en_IN")

random.seed(42)
np.random.seed(42)


# =========================================================
# 1. GENERATE CUSTOMERS
# =========================================================

customers = []

for i in range(NUM_CUSTOMERS):

    customers.append({
        "customer_id": f"customer-{i + 1:05d}",
        "name": fake.name(),
        "email": fake.email()
    })


# =========================================================
# 2. HELPER FUNCTIONS
# =========================================================

def random_transaction_time(start_date, end_date):

    seconds = int(
        (end_date - start_date).total_seconds()
    )

    return start_date + timedelta(
        seconds=random.randint(0, seconds)
    )


def generate_amount(high_value=False):

    if high_value:

        amount = np.random.uniform(
            10000,
            50000
        )

    else:

        amount = np.random.lognormal(
            mean=np.log(2000),
            sigma=0.8
        )

    return round(
        max(100, min(amount, 50000)),
        2
    )


def choose_failure_reason():

    return random.choice([
        "Temporary network failure",
        "Bank declined",
        "Payment timeout",
        "Insufficient funds",
        "Authentication failure"
    ])


# =========================================================
# 3. DATE RANGE
# =========================================================

start_date = datetime.now() - timedelta(days=90)

end_date = datetime.now()


# =========================================================
# 4. CUSTOMER BEHAVIOR STATE
# =========================================================

customer_stats = {}

for customer in customers:

    customer_stats[customer["customer_id"]] = {
        "transactions": 0,
        "failures": 0
    }


# =========================================================
# 5. GENERATE TRANSACTIONS
# =========================================================
# =========================================================
# 5. GENERATE TRANSACTIONS
# =========================================================

transactions = []


# ---------------------------------------------------------
# INCIDENT QUOTAS
# ---------------------------------------------------------

# We deliberately inject incidents instead of waiting for
# random transactions to match the incident conditions.

UPI_INCIDENT_COUNT = 3000
CARD_INCIDENT_COUNT = 2500
EVENING_INCIDENT_COUNT = 2500

INCIDENT_TOTAL = (
    UPI_INCIDENT_COUNT
    + CARD_INCIDENT_COUNT
    + EVENING_INCIDENT_COUNT
)

NORMAL_COUNT = (
    NUM_TRANSACTIONS
    - INCIDENT_TOTAL
)


# ---------------------------------------------------------
# HELPER TO CREATE TRANSACTION
# ---------------------------------------------------------

def create_transaction(
    customer,
    payment_method,
    device,
    location,
    transaction_time,
    amount,
    success_probability,
    incident_type=None
):

    customer_id = customer["customer_id"]

    stats = customer_stats[customer_id]

    # -----------------------------------------------------
    # Customer history BEFORE current transaction
    # -----------------------------------------------------

    previous_transactions = stats["transactions"]

    previous_failures = stats["failures"]

    if previous_transactions > 0:

        previous_success_rate = (
            previous_transactions - previous_failures
        ) / previous_transactions

    else:

        previous_success_rate = 1.0

    is_new_customer = (
        previous_transactions == 0
    )

    is_high_value = (
        amount >= 10000
    )

    # -----------------------------------------------------
    # Retry behavior
    # -----------------------------------------------------

    retry_count = random.choices(
        [0, 1, 2],
        weights=[0.85, 0.12, 0.03]
    )[0]

    attempt_number = retry_count + 1

    # -----------------------------------------------------
    # Transaction velocity
    # -----------------------------------------------------

    transaction_velocity = random.randint(
        1,
        5
    )

    # -----------------------------------------------------
    # Generate status
    # -----------------------------------------------------

    success = (
        random.random()
        < success_probability
    )

    if success:

        status = "SUCCESS"
        failure_reason = None

    else:

        status = "FAILED"

        failure_reason = choose_failure_reason()

    # -----------------------------------------------------
    # Update customer history
    # -----------------------------------------------------

    stats["transactions"] += 1

    if status == "FAILED":

        stats["failures"] += 1

    # -----------------------------------------------------
    # Create row
    # -----------------------------------------------------

    return {

        "transaction_id":
            f"txn-{len(transactions) + 1:07d}",

        "merchant_id":
            MERCHANT_ID,

        "customer_id":
            customer_id,

        "amount":
            amount,

        "currency":
            "INR",

        "payment_method":
            payment_method,

        "status":
            status,

        "failure_reason":
            failure_reason,

        "device":
            device,

        "location":
            location,

        "transaction_time":
            transaction_time,

        "attempt_number":
            attempt_number,

        # ML FEATURES

        "hour":
            transaction_time.hour,

        "day_of_week":
            transaction_time.weekday(),

        "is_high_value":
            is_high_value,

        "is_new_customer":
            is_new_customer,

        "previous_transactions":
            previous_transactions,

        "previous_failures":
            previous_failures,

        "previous_success_rate":
            round(
                previous_success_rate,
                4
            ),

        "retry_count":
            retry_count,

        "transaction_velocity":
            transaction_velocity,

        # GROUND TRUTH

        "is_incident":
            incident_type is not None,

        "incident_type":
            incident_type
    }


# =========================================================
# 5A. UPI DEGRADATION INCIDENT
# =========================================================
#
# UPI + ANDROID + Bengaluru + 20:00-23:00
#
# Target success rate: ~60%
# =========================================================

for _ in range(UPI_INCIDENT_COUNT):

    customer = random.choice(customers)

    transaction_date = (
        start_date
        + timedelta(
            days=random.randint(0, 89)
        )
    )

    transaction_time = transaction_date.replace(
        hour=random.randint(20, 23),
        minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )

    amount = generate_amount()

    transaction = create_transaction(
        customer=customer,
        payment_method="UPI",
        device="ANDROID",
        location="Bengaluru",
        transaction_time=transaction_time,
        amount=amount,
        success_probability=0.60,
        incident_type="UPI_DEGRADATION"
    )

    transactions.append(transaction)


# =========================================================
# 5B. HIGH-VALUE CARD DEGRADATION
# =========================================================
#
# CARD + IOS + Mumbai + amount > ₹10,000
#
# Target success rate: ~70%
# =========================================================

for _ in range(CARD_INCIDENT_COUNT):

    customer = random.choice(customers)

    transaction_time = random_transaction_time(
        start_date,
        end_date
    )

    amount = generate_amount(
        high_value=True
    )

    transaction = create_transaction(
        customer=customer,
        payment_method="CARD",
        device="IOS",
        location="Mumbai",
        transaction_time=transaction_time,
        amount=amount,
        success_probability=0.70,
        incident_type="HIGH_VALUE_CARD_DEGRADATION"
    )

    transactions.append(transaction)


# =========================================================
# 5C. EVENING DEGRADATION
# =========================================================
#
# 18:00-20:00
#
# Target success rate: ~72%
# =========================================================

for _ in range(EVENING_INCIDENT_COUNT):

    customer = random.choice(customers)

    transaction_date = (
        start_date
        + timedelta(
            days=random.randint(0, 89)
        )
    )

    transaction_time = transaction_date.replace(
        hour=random.randint(18, 20),
        minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )

    payment_method = random.choice(
        PAYMENT_METHODS
    )

    device = random.choice(
        DEVICES
    )

    location = random.choice(
        LOCATIONS
    )

    amount = generate_amount()

    transaction = create_transaction(
        customer=customer,
        payment_method=payment_method,
        device=device,
        location=location,
        transaction_time=transaction_time,
        amount=amount,
        success_probability=0.72,
        incident_type="EVENING_DEGRADATION"
    )

    transactions.append(transaction)


# =========================================================
# 5D. NORMAL TRANSACTIONS
# =========================================================

for _ in range(NORMAL_COUNT):

    customer = random.choice(customers)

    payment_method = random.choice(
        PAYMENT_METHODS
    )

    device = random.choice(
        DEVICES
    )

    location = random.choice(
        LOCATIONS
    )

    transaction_time = random_transaction_time(
        start_date,
        end_date
    )

    amount = generate_amount()

    success_probability = {
        "UPI": 0.90,
        "CARD": 0.94,
        "NETBANKING": 0.88,
        "WALLET": 0.91
    }[payment_method]

    # Slightly lower success probability for
    # high-value transactions.

    if amount >= 10000:

        success_probability -= 0.03

    transaction = create_transaction(
        customer=customer,
        payment_method=payment_method,
        device=device,
        location=location,
        transaction_time=transaction_time,
        amount=amount,
        success_probability=success_probability,
        incident_type=None
    )

    transactions.append(transaction)

# =========================================================
# 6. CREATE DATAFRAME
# =========================================================

df = pd.DataFrame(
    transactions
)


# =========================================================
# 7. SHUFFLE DATA
# =========================================================

df = df.sample(
    frac=1,
    random_state=42
).reset_index(
    drop=True
)


# =========================================================
# 8. SAVE DATASET
# =========================================================

df.to_csv(
    "data/generated_transactions.csv",
    index=False
)

pd.DataFrame(
    customers
).to_csv(
    "data/generated_customers.csv",
    index=False
)


# =========================================================
# 9. DATASET SUMMARY
# =========================================================

print("\n========================================")
print("      ML DATASET GENERATED")
print("========================================")

print(
    f"\nCustomers: {len(customers):,}"
)

print(
    f"Transactions: {len(df):,}"
)


# =========================================================
# STATUS
# =========================================================

print("\nStatus distribution:")

print(
    df["status"].value_counts()
)


# =========================================================
# PAYMENT METHODS
# =========================================================

print("\nPayment method distribution:")

print(
    df["payment_method"].value_counts()
)


# =========================================================
# INCIDENT DISTRIBUTION
# =========================================================

print("\nIncident distribution:")

print(
    df["incident_type"]
    .fillna("NORMAL")
    .value_counts()
)


# =========================================================
# INCIDENT SUCCESS RATES
# =========================================================

print("\nIncident success rates:")

incident_groups = (
    df
    .assign(
        incident_type=df["incident_type"]
        .fillna("NORMAL")
    )
    .groupby("incident_type")
)


for incident, group in incident_groups:

    success_rate = (
        group["status"] == "SUCCESS"
    ).mean() * 100

    print(
        f"{incident}: "
        f"{len(group):,} transactions | "
        f"{success_rate:.2f}% success"
    )


# =========================================================
# OVERALL SUCCESS RATE
# =========================================================

overall_success_rate = (
    df["status"] == "SUCCESS"
).mean() * 100

print(
    f"\nOverall success rate: "
    f"{overall_success_rate:.2f}%"
)


# =========================================================
# FEATURE CHECK
# =========================================================

print("\nML features:")

ml_features = [
    "hour",
    "day_of_week",
    "is_high_value",
    "is_new_customer",
    "previous_transactions",
    "previous_failures",
    "previous_success_rate",
    "retry_count",
    "transaction_velocity"
]

for feature in ml_features:

    print(
        f"  ✓ {feature}"
    )


print("\n========================================")
print("Dataset ready for ML training.")
print("========================================\n")