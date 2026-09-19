from pathlib import Path

import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "reconciliation_test_results.csv"
OUTPUT_FILE = DATA_DIR / "incident_classification_results.csv"


# ---------------------------------------------------------
# Incident classification mappings
# ---------------------------------------------------------

INCIDENT_CATEGORY_MAP = {
    "MISSING_EVENTS": "PAYMENT_STATE_INCONSISTENCY",
    "STATUS_CONFLICT": "PAYMENT_STATE_INCONSISTENCY",
    "MISSING_PENDING_EVENT": "PAYMENT_STATE_INCONSISTENCY",

    "MISSING_SETTLEMENT": "SETTLEMENT_RECONCILIATION",
    "DEBIT_WITHOUT_SETTLEMENT": "SETTLEMENT_RECONCILIATION",
    "MISSING_REVERSAL": "SETTLEMENT_RECONCILIATION",

    "PROVIDER_TIMEOUT": "PROVIDER_CONNECTIVITY",

    "POTENTIAL_DUPLICATE": "DUPLICATE_PAYMENT",

    "NONE": "NO_INCIDENT",
}


PRIORITY_MAP = {
    "DEBIT_WITHOUT_SETTLEMENT": "P1",
    "MISSING_SETTLEMENT": "P1",
    "STATUS_CONFLICT": "P1",

    "MISSING_EVENTS": "P2",
    "MISSING_REVERSAL": "P2",
    "PROVIDER_TIMEOUT": "P2",

    "MISSING_PENDING_EVENT": "P3",
    "POTENTIAL_DUPLICATE": "P3",

    "NONE": "NONE",
}


OWNER_MAP = {
    "DEBIT_WITHOUT_SETTLEMENT": "Payment Operations / Engineering",
    "MISSING_SETTLEMENT": "Payment Operations / Engineering",
    "STATUS_CONFLICT": "Payment Operations / Engineering",

    "MISSING_EVENTS": "Payment Operations",
    "MISSING_REVERSAL": "Payment Operations",
    "PROVIDER_TIMEOUT": "Provider Operations / Engineering",

    "MISSING_PENDING_EVENT": "Payment Operations",
    "POTENTIAL_DUPLICATE": "Payment Operations",

    "NONE": "Payment Operations",
}


ACTION_MAP = {
    "DEBIT_WITHOUT_SETTLEMENT":
        "Confirm whether the customer account was debited and investigate missing settlement confirmation.",

    "MISSING_SETTLEMENT":
        "Investigate settlement records and confirm whether settlement was completed.",

    "STATUS_CONFLICT":
        "Review transaction and event records to determine the authoritative payment state.",

    "MISSING_EVENTS":
        "Investigate missing payment events and verify the transaction lifecycle.",

    "MISSING_REVERSAL":
        "Confirm whether a reversal occurred and investigate the missing reversal event.",

    "PROVIDER_TIMEOUT":
        "Review provider logs and request/response records for timeout details.",

    "MISSING_PENDING_EVENT":
        "Verify the transaction state and investigate the missing pending event.",

    "POTENTIAL_DUPLICATE":
        "Review matching transaction attributes and determine whether the payment was duplicated.",

    "NONE":
        "No incident investigation required.",
}


# ---------------------------------------------------------
# Classification function
# ---------------------------------------------------------

def classify_incidents(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify reconciliation incidents into operational categories,
    investigation priorities, owners, and recommended actions.

    Parameters
    ----------
    df : pandas.DataFrame
        Reconciliation results.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing incident classification fields.
    """

    result = df.copy()

    # Make sure incident_type exists
    if "incident_type" not in result.columns:
        raise ValueError(
            "Input DataFrame must contain an 'incident_type' column."
        )

    # -----------------------------------------------------
    # Incident category
    # -----------------------------------------------------

    result["incident_category"] = (
        result["incident_type"]
        .map(INCIDENT_CATEGORY_MAP)
        .fillna("UNKNOWN")
    )

    # -----------------------------------------------------
    # Investigation priority
    # -----------------------------------------------------

    result["priority"] = (
        result["incident_type"]
        .map(PRIORITY_MAP)
        .fillna("NONE")
    )

    # -----------------------------------------------------
    # Recommended owner
    # -----------------------------------------------------

    result["recommended_owner"] = (
        result["incident_type"]
        .map(OWNER_MAP)
        .fillna("Payment Operations")
    )

    # -----------------------------------------------------
    # Recommended action
    # -----------------------------------------------------

    result["recommended_action"] = (
        result["incident_type"]
        .map(ACTION_MAP)
        .fillna("Review the transaction and investigate the incident.")
    )

    return result


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------

def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Reconciliation results not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    result = classify_incidents(df)

    result.to_csv(OUTPUT_FILE, index=False)

    print("Incident classification completed.")
    print(f"Total transactions: {len(result):,}")

    print("\nIncident categories:")
    print(result["incident_category"].value_counts())

    print("\nInvestigation priorities:")
    print(result["priority"].value_counts())

    print("\nRecommended ownership:")
    print(result["recommended_owner"].value_counts())

    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()