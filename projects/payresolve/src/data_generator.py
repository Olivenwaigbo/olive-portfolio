"""
PayResolve - Synthetic Payment Data Generator

Generates realistic synthetic payment transactions and payment events
for development and testing.

No real customer or financial information is used.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

fake = Faker()

RANDOM_SEED = 42

random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

NUM_TRANSACTIONS = 10_000

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TRANSACTIONS_FILE = DATA_DIR / "transactions.csv"
EVENTS_FILE = DATA_DIR / "events.csv"


# ---------------------------------------------------------
# PAYMENT CONFIGURATION
# ---------------------------------------------------------

PROVIDERS = [
    "Provider A",
    "Provider B",
    "Provider C",
    "Provider D",
]

BANKS = [
    "Bank Alpha",
    "Bank Beta",
    "Bank Gamma",
    "Bank Delta",
    "Bank Epsilon",
]

CURRENCIES = ["NGN"]

PAYMENT_METHODS = [
    "Bank Transfer",
    "Card",
    "USSD",
    "Wallet",
]

FINAL_STATUSES = [
    "SUCCESS",
    "FAILED",
    "PENDING",
    "REVERSED",
]

FAILURE_REASONS = [
    "INSUFFICIENT_FUNDS",
    "PROVIDER_ERROR",
    "TIMEOUT",
    "NETWORK_ERROR",
    "INVALID_ACCOUNT",
    "WEBHOOK_FAILURE",
]

MERCHANT_CATEGORIES = [
    "E-commerce",
    "Food & Delivery",
    "Transport",
    "Utilities",
    "Education",
    "Healthcare",
    "Entertainment",
    "Retail",
]


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def generate_transaction_id() -> str:
    """Generate a unique transaction ID."""
    return f"TXN-{uuid.uuid4().hex[:10].upper()}"


def generate_customer_id() -> str:
    """Generate a synthetic customer ID."""
    return f"CUST-{random.randint(100000, 999999)}"


def generate_merchant_id() -> str:
    """Generate a synthetic merchant ID."""
    return f"MER-{random.randint(1000, 9999)}"


def random_amount() -> float:
    """
    Generate a realistic synthetic Nigerian transaction amount.
    """
    amount = random.choice(
        [
            random.randint(500, 10_000),
            random.randint(10_000, 50_000),
            random.randint(50_000, 250_000),
            random.randint(250_000, 1_000_000),
        ]
    )

    return float(amount)


def random_timestamp() -> datetime:
    """
    Generate a timestamp within the previous 30 days.
    """
    end = datetime.now()
    start = end - timedelta(days=30)

    random_seconds = random.randint(
        0,
        int((end - start).total_seconds()),
    )

    return start + timedelta(seconds=random_seconds)


def choose_final_status() -> str:
    """
    Generate a weighted payment outcome.

    Most transactions succeed, while a smaller percentage
    experience failure, pending or reversal states.
    """

    return random.choices(
        FINAL_STATUSES,
        weights=[
            0.78,  # SUCCESS
            0.10,  # FAILED
            0.08,  # PENDING
            0.04,  # REVERSED
        ],
        k=1,
    )[0]


# ---------------------------------------------------------
# EVENT GENERATION
# ---------------------------------------------------------

def create_events(
    transaction: dict,
    final_status: str,
) -> list[dict]:
    """
    Create a realistic event timeline for a transaction.
    """

    transaction_id = transaction["transaction_id"]
    initiated_at = transaction["created_at"]

    events = []

    # Event 1 — payment initiated
    events.append(
        {
            "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
            "transaction_id": transaction_id,
            "event_type": "INITIATED",
            "event_status": "RECEIVED",
            "event_timestamp": initiated_at,
            "provider": transaction["provider"],
        }
    )

    # Event 2 — processing
    processing_time = initiated_at + timedelta(
        seconds=random.randint(1, 5)
    )

    events.append(
        {
            "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
            "transaction_id": transaction_id,
            "event_type": "PROCESSING",
            "event_status": "RECEIVED",
            "event_timestamp": processing_time,
            "provider": transaction["provider"],
        }
    )

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    if final_status == "SUCCESS":

        success_time = processing_time + timedelta(
            seconds=random.randint(1, 15)
        )

        events.append(
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
                "transaction_id": transaction_id,
                "event_type": "SUCCESS",
                "event_status": "CONFIRMED",
                "event_timestamp": success_time,
                "provider": transaction["provider"],
            }
        )

        settlement_time = success_time + timedelta(
            seconds=random.randint(1, 10)
        )

        events.append(
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
                "transaction_id": transaction_id,
                "event_type": "SETTLEMENT",
                "event_status": "CONFIRMED",
                "event_timestamp": settlement_time,
                "provider": transaction["provider"],
            }
        )

    # -----------------------------------------------------
    # FAILED
    # -----------------------------------------------------

    elif final_status == "FAILED":

        failure_reason = random.choice(FAILURE_REASONS)

        failure_time = processing_time + timedelta(
            seconds=random.randint(5, 30)
        )

        events.append(
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
                "transaction_id": transaction_id,
                "event_type": "FAILED",
                "event_status": failure_reason,
                "event_timestamp": failure_time,
                "provider": transaction["provider"],
            }
        )

    # -----------------------------------------------------
    # PENDING
    # -----------------------------------------------------

    elif final_status == "PENDING":

        pending_time = processing_time + timedelta(
            seconds=random.randint(5, 30)
        )

        events.append(
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
                "transaction_id": transaction_id,
                "event_type": "PENDING",
                "event_status": "AWAITING_CONFIRMATION",
                "event_timestamp": pending_time,
                "provider": transaction["provider"],
            }
        )

    # -----------------------------------------------------
    # REVERSED
    # -----------------------------------------------------

    elif final_status == "REVERSED":

        success_time = processing_time + timedelta(
            seconds=random.randint(1, 10)
        )

        events.append(
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
                "transaction_id": transaction_id,
                "event_type": "SUCCESS",
                "event_status": "CONFIRMED",
                "event_timestamp": success_time,
                "provider": transaction["provider"],
            }
        )

        reversal_time = success_time + timedelta(
            seconds=random.randint(30, 300)
        )

        events.append(
            {
                "event_id": f"EVT-{uuid.uuid4().hex[:10].upper()}",
                "transaction_id": transaction_id,
                "event_type": "REVERSAL",
                "event_status": "REVERSED",
                "event_timestamp": reversal_time,
                "provider": transaction["provider"],
            }
        )

    return events


# ---------------------------------------------------------
# TRANSACTION GENERATION
# ---------------------------------------------------------

def generate_transactions(
    number_of_transactions: int = NUM_TRANSACTIONS,
) -> tuple[list[dict], list[dict]]:
    """
    Generate synthetic transactions and their corresponding events.
    """

    transactions = []
    events = []

    for _ in range(number_of_transactions):

        transaction_id = generate_transaction_id()

        created_at = random_timestamp()

        final_status = choose_final_status()

        transaction = {
            "transaction_id": transaction_id,
            "customer_id": generate_customer_id(),
            "merchant_id": generate_merchant_id(),
            "merchant_category": random.choice(
                MERCHANT_CATEGORIES
            ),
            "provider": random.choice(PROVIDERS),
            "bank": random.choice(BANKS),
            "payment_method": random.choice(PAYMENT_METHODS),
            "currency": random.choice(CURRENCIES),
            "amount": random_amount(),
            "created_at": created_at,
            "status": final_status,
        }

        transactions.append(transaction)

        transaction_events = create_events(
            transaction,
            final_status,
        )

        events.extend(transaction_events)

    return transactions, events


# ---------------------------------------------------------
# SAVE DATA
# ---------------------------------------------------------

def save_data(
    transactions: list[dict],
    events: list[dict],
) -> None:
    """
    Save generated transactions and events as CSV files.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    transactions_df = pd.DataFrame(transactions)

    events_df = pd.DataFrame(events)

    transactions_df.to_csv(
        TRANSACTIONS_FILE,
        index=False,
    )

    events_df.to_csv(
        EVENTS_FILE,
        index=False,
    )

    print(
        f"Saved {len(transactions_df):,} transactions to:"
    )

    print(TRANSACTIONS_FILE)

    print()

    print(
        f"Saved {len(events_df):,} payment events to:"
    )

    print(EVENTS_FILE)


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main() -> None:
    print("=" * 60)

    print("PAYRESOLVE — SYNTHETIC PAYMENT DATA GENERATOR")

    print("=" * 60)

    print()

    print(
        f"Generating {NUM_TRANSACTIONS:,} synthetic transactions..."
    )

    print()

    transactions, events = generate_transactions()

    save_data(
        transactions,
        events,
    )

    print()

    print("Generation complete.")

    print("=" * 60)


if __name__ == "__main__":
    main()