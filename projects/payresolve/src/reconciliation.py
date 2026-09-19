from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TRANSACTIONS_FILE = DATA_DIR / "transactions_test.csv"
EVENTS_FILE = DATA_DIR / "events_test.csv"
OUTPUT_FILE = DATA_DIR / "reconciliation_test_results.csv"


def reconcile_transactions():
    """
    Reconcile payment transactions against their recorded payment events.

    Returns:
        pandas.DataFrame: Transaction-level reconciliation results.
    """

    if not TRANSACTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Transactions dataset not found: {TRANSACTIONS_FILE}"
        )

    if not EVENTS_FILE.exists():
        raise FileNotFoundError(
            f"Events dataset not found: {EVENTS_FILE}"
        )

    transactions = pd.read_csv(TRANSACTIONS_FILE)
    events = pd.read_csv(EVENTS_FILE)

    # ---------------------------------------------------------
    # Summarise events for each transaction
    # ---------------------------------------------------------

    event_summary = (
        events.groupby("transaction_id")
        .agg(
            event_count=("event_id", "count"),
            has_success=("event_type", lambda x: (x == "SUCCESS").any()),
            has_settlement=("event_type", lambda x: (x == "SETTLEMENT").any()),
            has_reversal=("event_type", lambda x: (x == "REVERSAL").any()),
            has_failure=("event_type", lambda x: (x == "FAILED").any()),
            has_pending=("event_type", lambda x: (x == "PENDING").any()),
            has_timeout=(
                "event_status",
                lambda x: (x == "TIMEOUT").any()
            ),
            has_debit=(
                "event_type",
                lambda x: (x == "DEBIT").any()
            ),
        )
        .reset_index()
    )

    # ---------------------------------------------------------
    # Merge transaction data with event information
    # ---------------------------------------------------------

    result = transactions.merge(
        event_summary,
        on="transaction_id",
        how="left",
    )

    boolean_columns = [
        "has_success",
        "has_settlement",
        "has_reversal",
        "has_failure",
        "has_pending",
        "has_timeout",
        "has_debit",
    ]

    for column in boolean_columns:
        result[column] = result[column].fillna(False).astype(bool)

    result["event_count"] = result["event_count"].fillna(0).astype(int)

    # ---------------------------------------------------------
    # Detect potential duplicate payments
    # ---------------------------------------------------------

    duplicate_keys = [
        "customer_id",
        "merchant_id",
        "amount",
        "provider",
        "payment_method",
    ]

    result["potential_duplicate"] = result.duplicated(
        subset=duplicate_keys,
        keep=False,
    )

    # ---------------------------------------------------------
    # Default reconciliation state
    # ---------------------------------------------------------

    result["reconciliation_status"] = "RECONCILED"
    result["incident_type"] = "NONE"
    result["severity"] = "LOW"

    # ---------------------------------------------------------
    # Apply reconciliation rules
    # ---------------------------------------------------------

    def set_exception(mask, incident_type, severity):
        """
        Apply an incident classification while preserving
        stronger existing incidents.
        """

        result.loc[
            mask & (result["reconciliation_status"] == "RECONCILED"),
            "reconciliation_status",
        ] = "EXCEPTION"

        result.loc[
            mask & (result["incident_type"] == "NONE"),
            "incident_type",
        ] = incident_type

        result.loc[
            mask & (result["severity"] == "LOW"),
            "severity",
        ] = severity

    # No payment events recorded
    set_exception(
        result["event_count"] == 0,
        "MISSING_EVENTS",
        "HIGH",
    )

    # Successful transaction without settlement
    set_exception(
        (result["status"] == "SUCCESS")
        & result["has_success"]
        & ~result["has_settlement"],
        "MISSING_SETTLEMENT",
        "HIGH",
    )

    # Failed transaction that contains a success event
    set_exception(
        (result["status"] == "FAILED")
        & result["has_success"],
        "STATUS_CONFLICT",
        "HIGH",
    )

    # Reversed transaction without reversal event
    set_exception(
        (result["status"] == "REVERSED")
        & ~result["has_reversal"],
        "MISSING_REVERSAL",
        "MEDIUM",
    )

    # Pending transaction without pending event
    set_exception(
        (result["status"] == "PENDING")
        & ~result["has_pending"],
        "MISSING_PENDING_EVENT",
        "MEDIUM",
    )

    # Provider timeout
    set_exception(
        result["has_timeout"],
        "PROVIDER_TIMEOUT",
        "MEDIUM",
    )

    # Debit received but no settlement
    set_exception(
        result["has_debit"] & ~result["has_settlement"],
        "DEBIT_WITHOUT_SETTLEMENT",
        "HIGH",
    )

    # Potential duplicate
    set_exception(
        result["potential_duplicate"],
        "POTENTIAL_DUPLICATE",
        "MEDIUM",
    )

    # ---------------------------------------------------------
    # Save results
    # ---------------------------------------------------------

    result.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return result


def main():
    result = reconcile_transactions()

    print(f"Total transactions: {len(result):,}")

    exceptions = result[
        result["reconciliation_status"] == "EXCEPTION"
    ]

    reconciled = result[
        result["reconciliation_status"] == "RECONCILED"
    ]

    print(f"Reconciliation exceptions: {len(exceptions):,}")
    print(f"Reconciled transactions: {len(reconciled):,}")

    print("\nIncident breakdown:")
    print(result["incident_type"].value_counts())

    print("\nSeverity:")
    print(result["severity"].value_counts())

    potential_duplicates = result[
        result["potential_duplicate"]
    ]

    print(
        f"\nPotential duplicates: "
        f"{len(potential_duplicates):,}"
    )

    print(
        f"\nResults saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()