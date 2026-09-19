"""
PayResolve - Payment Scenario Injection Engine

Creates controlled payment incidents inside the synthetic dataset
so that the reconciliation and anomaly-detection systems can be tested.

No real payment or customer data is used.
"""

from __future__ import annotations

import random
import uuid
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

RANDOM_SEED = 42

random.seed(RANDOM_SEED)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TRANSACTIONS_FILE = DATA_DIR / "transactions.csv"
EVENTS_FILE = DATA_DIR / "events.csv"

OUTPUT_TRANSACTIONS_FILE = DATA_DIR / "transactions_test.csv"
OUTPUT_EVENTS_FILE = DATA_DIR / "events_test.csv"


# Number of incidents to create
INCIDENTS_PER_TYPE = 20


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def create_event_id() -> str:
    """Create a synthetic event ID."""
    return f"EVT-{uuid.uuid4().hex[:10].upper()}"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the clean synthetic payment dataset."""

    if not TRANSACTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Missing transaction file: {TRANSACTIONS_FILE}"
        )

    if not EVENTS_FILE.exists():
        raise FileNotFoundError(
            f"Missing events file: {EVENTS_FILE}"
        )

    transactions = pd.read_csv(
        TRANSACTIONS_FILE,
        parse_dates=["created_at"],
    )

    events = pd.read_csv(
        EVENTS_FILE,
        parse_dates=["event_timestamp"],
    )

    return transactions, events


# ---------------------------------------------------------
# SCENARIO 1
# MISSING SETTLEMENT
# ---------------------------------------------------------

def inject_missing_settlement(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    number: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    candidates = transactions[
        transactions["status"] == "SUCCESS"
    ]

    selected = candidates.sample(
        n=min(number, len(candidates)),
        random_state=RANDOM_SEED,
    )

    for transaction_id in selected["transaction_id"]:

        mask = (
            (events["transaction_id"] == transaction_id)
            & (events["event_type"] == "SETTLEMENT")
        )

        events = events.loc[~mask].copy()

    return transactions, events


# ---------------------------------------------------------
# SCENARIO 2
# STATUS CONFLICT
# ---------------------------------------------------------

def inject_status_conflict(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    number: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    candidates = transactions[
        transactions["status"] == "FAILED"
    ]

    selected = candidates.sample(
        n=min(number, len(candidates)),
        random_state=RANDOM_SEED + 1,
    )

    for transaction_id in selected["transaction_id"]:

        transaction_events = events[
            events["transaction_id"] == transaction_id
        ]

        if transaction_events.empty:
            continue

        source_event = transaction_events.iloc[0]

        new_event = {
            "event_id": create_event_id(),
            "transaction_id": transaction_id,
            "event_type": "SUCCESS",
            "event_status": "CONFIRMED",
            "event_timestamp": source_event["event_timestamp"],
            "provider": source_event["provider"],
        }

        events = pd.concat(
            [
                events,
                pd.DataFrame([new_event]),
            ],
            ignore_index=True,
        )

    return transactions, events


# ---------------------------------------------------------
# SCENARIO 3
# MISSING EVENTS
# ---------------------------------------------------------

def inject_missing_events(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    number: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    selected = transactions.sample(
        n=min(number, len(transactions)),
        random_state=RANDOM_SEED + 2,
    )

    selected_ids = set(
        selected["transaction_id"]
    )

    events = events[
        ~events["transaction_id"].isin(selected_ids)
    ].copy()

    return transactions, events


# ---------------------------------------------------------
# SCENARIO 4
# PROVIDER TIMEOUT
# ---------------------------------------------------------

def inject_provider_timeout(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    number: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    candidates = transactions[
        transactions["status"].isin(
            ["SUCCESS", "PENDING"]
        )
    ]

    selected = candidates.sample(
        n=min(number, len(candidates)),
        random_state=RANDOM_SEED + 3,
    )

    for transaction_id in selected["transaction_id"]:

        transaction_events = events[
            events["transaction_id"] == transaction_id
        ]

        if transaction_events.empty:
            continue

        source_event = transaction_events.iloc[0]

        timeout_event = {
            "event_id": create_event_id(),
            "transaction_id": transaction_id,
            "event_type": "PROVIDER_RESPONSE",
            "event_status": "TIMEOUT",
            "event_timestamp": source_event["event_timestamp"],
            "provider": source_event["provider"],
        }

        events = pd.concat(
            [
                events,
                pd.DataFrame([timeout_event]),
            ],
            ignore_index=True,
        )

    return transactions, events


# ---------------------------------------------------------
# SCENARIO 5
# DUPLICATE PAYMENT
# ---------------------------------------------------------

def inject_duplicate_payment(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    number: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    selected = transactions.sample(
        n=min(number, len(transactions)),
        random_state=RANDOM_SEED + 4,
    )

    duplicates = []

    duplicate_events = []

    for _, transaction in selected.iterrows():

        original_id = transaction["transaction_id"]

        duplicate_id = (
            f"{original_id}-DUP"
        )

        duplicate = transaction.copy()

        duplicate["transaction_id"] = duplicate_id

        duplicates.append(duplicate)

        original_events = events[
            events["transaction_id"] == original_id
        ]

        for _, event in original_events.iterrows():

            duplicate_event = event.copy()

            duplicate_event["event_id"] = create_event_id()

            duplicate_event[
                "transaction_id"
            ] = duplicate_id

            duplicate_events.append(
                duplicate_event
            )

    if duplicates:

        transactions = pd.concat(
            [
                transactions,
                pd.DataFrame(duplicates),
            ],
            ignore_index=True,
        )

    if duplicate_events:

        events = pd.concat(
            [
                events,
                pd.DataFrame(duplicate_events),
            ],
            ignore_index=True,
        )

    return transactions, events


# ---------------------------------------------------------
# SCENARIO 6
# DEBIT WITHOUT SETTLEMENT
# ---------------------------------------------------------

def inject_debit_without_settlement(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
    number: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    candidates = transactions[
        transactions["status"] == "SUCCESS"
    ]

    selected = candidates.sample(
        n=min(number, len(candidates)),
        random_state=RANDOM_SEED + 5,
    )

    for transaction_id in selected["transaction_id"]:

        transaction_events = events[
            events["transaction_id"] == transaction_id
        ]

        if transaction_events.empty:
            continue

        source_event = transaction_events.iloc[0]

        debit_event = {
            "event_id": create_event_id(),
            "transaction_id": transaction_id,
            "event_type": "DEBIT",
            "event_status": "CONFIRMED",
            "event_timestamp": source_event["event_timestamp"],
            "provider": source_event["provider"],
        }

        events = pd.concat(
            [
                events,
                pd.DataFrame([debit_event]),
            ],
            ignore_index=True,
        )

        # Remove settlement so that the transaction
        # represents a potential debit without settlement.
        settlement_mask = (
            (events["transaction_id"] == transaction_id)
            & (events["event_type"] == "SETTLEMENT")
        )

        events = events.loc[
            ~settlement_mask
        ].copy()

    return transactions, events


# ---------------------------------------------------------
# MAIN INJECTION PIPELINE
# ---------------------------------------------------------

def inject_scenarios(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:

    print()
    print("Injecting controlled payment incidents...")
    print()

    transactions, events = inject_missing_settlement(
        transactions,
        events,
        INCIDENTS_PER_TYPE,
    )

    print(
        "✓ Missing settlement scenarios injected"
    )

    transactions, events = inject_status_conflict(
        transactions,
        events,
        INCIDENTS_PER_TYPE,
    )

    print(
        "✓ Status conflict scenarios injected"
    )

    transactions, events = inject_missing_events(
        transactions,
        events,
        INCIDENTS_PER_TYPE,
    )

    print(
        "✓ Missing event scenarios injected"
    )

    transactions, events = inject_provider_timeout(
        transactions,
        events,
        INCIDENTS_PER_TYPE,
    )

    print(
        "✓ Provider timeout scenarios injected"
    )

    transactions, events = inject_duplicate_payment(
        transactions,
        events,
        INCIDENTS_PER_TYPE,
    )

    print(
        "✓ Duplicate payment scenarios injected"
    )

    transactions, events = inject_debit_without_settlement(
        transactions,
        events,
        INCIDENTS_PER_TYPE,
    )

    print(
        "✓ Debit/settlement mismatch scenarios injected"
    )

    return transactions, events


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

def save_test_dataset(
    transactions: pd.DataFrame,
    events: pd.DataFrame,
) -> None:

    transactions.to_csv(
        OUTPUT_TRANSACTIONS_FILE,
        index=False,
    )

    events.to_csv(
        OUTPUT_EVENTS_FILE,
        index=False,
    )

    print()
    print(
        f"Test transactions saved to:\n"
        f"{OUTPUT_TRANSACTIONS_FILE}"
    )

    print()

    print(
        f"Test events saved to:\n"
        f"{OUTPUT_EVENTS_FILE}"
    )


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main() -> None:

    print("=" * 60)
    print("PAYRESOLVE — SCENARIO INJECTION ENGINE")
    print("=" * 60)

    transactions, events = load_data()

    print()
    print(
        f"Original transactions: {len(transactions):,}"
    )

    print(
        f"Original events: {len(events):,}"
    )

    transactions, events = inject_scenarios(
        transactions,
        events,
    )

    save_test_dataset(
        transactions,
        events,
    )

    print()
    print(
        f"Final transactions: {len(transactions):,}"
    )

    print(
        f"Final events: {len(events):,}"
    )

    print()
    print("Scenario injection complete.")

    print("=" * 60)


if __name__ == "__main__":
    main()