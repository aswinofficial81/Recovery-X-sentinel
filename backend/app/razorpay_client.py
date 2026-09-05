import os
from pathlib import Path

import razorpay
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# =========================================================
# RAZORPAY CREDENTIALS
# =========================================================

RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_KEY_ID"
)

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET"
)


if not RAZORPAY_KEY_ID:
    raise ValueError(
        "RAZORPAY_KEY_ID is missing from backend/.env"
    )


if not RAZORPAY_KEY_SECRET:
    raise ValueError(
        "RAZORPAY_KEY_SECRET is missing from backend/.env"
    )


# =========================================================
# RAZORPAY CLIENT
# =========================================================

client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


# =========================================================
# CREATE TEST ORDER
# =========================================================

def create_test_order(
    amount,
    currency="INR",
    receipt=None
):

    amount_paise = int(
        round(
            float(amount) * 100
        )
    )


    if receipt is None:

        receipt = (
            "recovery_"
            + str(
                abs(
                    hash(
                        str(amount)
                    )
                )
            )
        )


    order_data = {

        "amount":
            amount_paise,

        "currency":
            currency,

        "receipt":
            receipt,

        "notes": {

            "source":
                "Revenue_AutoPilot",

            "environment":
                "test"
        }
    }


    order = client.order.create(
        data=order_data
    )


    return order


# =========================================================
# FETCH ORDER
# =========================================================

def fetch_order(
    order_id
):

    return client.order.fetch(
        order_id
    )


# =========================================================
# FETCH PAYMENT
# =========================================================

def fetch_payment(
    payment_id
):

    return client.payment.fetch(
        payment_id
    )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print("\n========================================")
    print("       RAZORPAY TEST CONNECTION")
    print("========================================")


    print(
        "\nCreating test order..."
    )


    try:

        order = create_test_order(
            amount=500,
            receipt="recovery_test_001"
        )


        print(
            "\n✓ Razorpay connection successful"
        )


        print(
            f"Order ID: "
            f"{order['id']}"
        )


        print(
            f"Amount: "
            f"₹{order['amount'] / 100:,.2f}"
        )


        print(
            f"Currency: "
            f"{order['currency']}"
        )


        print(
            f"Status: "
            f"{order['status']}"
        )


    except Exception as e:

        print(
            "\n✗ Razorpay connection failed"
        )

        print(
            f"Error: {e}"
        )


    print(
        "\n========================================"
    )