import os

import pandas as pd
import psycopg2
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv("backend/.env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD
]):
    raise ValueError(
        "Database configuration is incomplete"
    )


# =========================================================
# CONNECT TO DATABASE
# =========================================================

connection = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

cursor = connection.cursor()


try:

    # =====================================================
    # 1. FIND DEMO MERCHANT
    # =====================================================

    cursor.execute("""
        SELECT id
        FROM merchants
        WHERE email = 'demo@example.com'
        LIMIT 1;
    """)

    merchant_result = cursor.fetchone()

    if not merchant_result:

        raise ValueError(
            "Demo merchant not found. "
            "Create the merchant first."
        )

    merchant_id = merchant_result[0]

    print("Merchant found:", merchant_id)


    # =====================================================
    # 2. REMOVE OLD DEMO DATA
    # =====================================================

    print("\nRemoving old demo data...")




    # -----------------------------------------------------
    # Remove old revenue leaks
    # -----------------------------------------------------

    cursor.execute("""
        DELETE FROM revenue_leaks
        WHERE merchant_id = %s;
    """, (merchant_id,))


    # -----------------------------------------------------
    # Remove old transactions
    # -----------------------------------------------------

    cursor.execute("""
        DELETE FROM transactions
        WHERE merchant_id = %s;
    """, (merchant_id,))


    # -----------------------------------------------------
    # Remove old customers
    # -----------------------------------------------------

    cursor.execute("""
        DELETE FROM customers
        WHERE merchant_id = %s;
    """, (merchant_id,))


    print("Old demo data removed.")


    # =====================================================
    # 3. LOAD CUSTOMERS CSV
    # =====================================================

    customers_df = pd.read_csv(
        "data/generated_customers.csv"
    )

    customer_id_map = {}


    print(
        f"\nLoading {len(customers_df):,} customers..."
    )


    for _, row in customers_df.iterrows():

        cursor.execute(
            """
            INSERT INTO customers (
                merchant_id,
                name,
                email
            )
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (
                merchant_id,
                row["name"],
                row["email"]
            )
        )

        postgres_customer_id = (
            cursor.fetchone()[0]
        )

        customer_id_map[
            row["customer_id"]
        ] = postgres_customer_id


    print(
        "Customers inserted:",
        len(customer_id_map)
    )


    # =====================================================
    # 4. LOAD TRANSACTIONS CSV
    # =====================================================

    transactions_df = pd.read_csv(
        "data/generated_transactions.csv"
    )


    print(
        f"\nLoading "
        f"{len(transactions_df):,} transactions..."
    )


    inserted_transactions = 0


    for _, row in transactions_df.iterrows():

        synthetic_customer_id = (
            row["customer_id"]
        )

        if synthetic_customer_id not in customer_id_map:

            raise ValueError(
                f"Customer not found: "
                f"{synthetic_customer_id}"
            )

        postgres_customer_id = (
            customer_id_map[
                synthetic_customer_id
            ]
        )


        cursor.execute(
            """
            INSERT INTO transactions (
                merchant_id,
                customer_id,
                amount,
                currency,
                payment_method,
                status,
                failure_reason,
                device,
                location,
                transaction_time,
                attempt_number
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            );
            """,
            (
                merchant_id,
                postgres_customer_id,
                float(row["amount"]),
                row["currency"],
                row["payment_method"],
                row["status"],
                (
                    row["failure_reason"]
                    if pd.notna(
                        row["failure_reason"]
                    )
                    else None
                ),
                row["device"],
                row["location"],
                pd.to_datetime(
                    row["transaction_time"]
                ),
                int(row["attempt_number"])
            )
        )


        inserted_transactions += 1


        # Progress indicator every 5,000 rows

        if inserted_transactions % 5000 == 0:

            print(
                f"  Inserted "
                f"{inserted_transactions:,} "
                f"transactions..."
            )


    print(
        "\nTransactions inserted:",
        inserted_transactions
    )


    # =====================================================
    # 5. COMMIT
    # =====================================================

    connection.commit()


    # =====================================================
    # 6. DATABASE VERIFICATION
    # =====================================================

    print("\nVerifying database...")


    cursor.execute("""
        SELECT COUNT(*)
        FROM customers
        WHERE merchant_id = %s;
    """, (merchant_id,))

    customer_count = cursor.fetchone()[0]


    cursor.execute("""
        SELECT COUNT(*)
        FROM transactions
        WHERE merchant_id = %s;
    """, (merchant_id,))

    transaction_count = cursor.fetchone()[0]


    cursor.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE status = 'SUCCESS'
            ),
            COUNT(*) FILTER (
                WHERE status = 'FAILED'
            )
        FROM transactions
        WHERE merchant_id = %s;
    """, (merchant_id,))

    success_count, failure_count = (
        cursor.fetchone()
    )


    print("\n========================================")
    print("       DATABASE LOAD SUCCESSFUL")
    print("========================================")

    print(
        f"\nCustomers in database: "
        f"{customer_count:,}"
    )

    print(
        f"Transactions in database: "
        f"{transaction_count:,}"
    )

    print(
        f"Successful transactions: "
        f"{success_count:,}"
    )

    print(
        f"Failed transactions: "
        f"{failure_count:,}"
    )


    if transaction_count > 0:

        success_rate = (
            success_count
            / transaction_count
            * 100
        )

        print(
            f"Success rate: "
            f"{success_rate:.2f}%"
        )


    print("\n========================================")


except Exception as e:

    # =====================================================
    # ROLLBACK IF ANYTHING FAILS
    # =====================================================

    connection.rollback()

    print(
        "\nERROR: Database loading failed."
    )

    print(
        "All database changes have been rolled back."
    )

    print(
        f"\nDetails: {e}"
    )

    raise


finally:

    cursor.close()
    connection.close()

    print(
        "\nDatabase connection closed."
    )