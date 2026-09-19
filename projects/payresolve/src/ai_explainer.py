from pathlib import Path
import json
import os

import pandas as pd
from dotenv import load_dotenv
from groq import Groq


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

TRANSACTIONS_FILE = DATA_DIR / "transactions_test.csv"
EVENTS_FILE = DATA_DIR / "events_test.csv"
ANOMALY_FILE = DATA_DIR / "anomaly_detection_results.csv"
OUTPUT_FILE = DATA_DIR / "ai_explanations.csv"

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# =========================================================
# GROQ CONFIGURATION
# =========================================================

MODEL_NAME = "openai/gpt-oss-20b"


def get_groq_client():
    """
    Create a Groq client using the API key stored in .env.
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY was not found. "
            "Add your Groq API key to the .env file."
        )

    return Groq(api_key=api_key)


# =========================================================
# DATA LOADING
# =========================================================

def load_investigation_data():
    """
    Load the datasets required to construct the evidence package.
    """

    required_files = [
        TRANSACTIONS_FILE,
        EVENTS_FILE,
        ANOMALY_FILE,
    ]

    for file_path in required_files:
        if not file_path.exists():
            raise FileNotFoundError(
                f"Required data file not found: {file_path}"
            )

    transactions_df = pd.read_csv(TRANSACTIONS_FILE)
    events_df = pd.read_csv(EVENTS_FILE)
    anomaly_df = pd.read_csv(ANOMALY_FILE)

    return transactions_df, events_df, anomaly_df


# =========================================================
# EVIDENCE CONSTRUCTION
# =========================================================

def build_transaction_evidence(transaction_id):
    """
    Build an evidence package for one transaction.

    The evidence package contains only facts already present
    in the PayResolve datasets.
    """

    (
        transactions_df,
        events_df,
        anomaly_df,
    ) = load_investigation_data()

    transaction_matches = transactions_df[
        transactions_df["transaction_id"] == transaction_id
    ]

    if transaction_matches.empty:
        raise ValueError(
            f"Transaction {transaction_id} was not found."
        )

    transaction = transaction_matches.iloc[0].to_dict()

    anomaly_matches = anomaly_df[
        anomaly_df["transaction_id"] == transaction_id
    ]

    if anomaly_matches.empty:
        raise ValueError(
            f"Anomaly record for {transaction_id} was not found."
        )

    anomaly = anomaly_matches.iloc[0].to_dict()

    timeline = events_df[
        events_df["transaction_id"] == transaction_id
    ].copy()

    if not timeline.empty:
        timeline = timeline.sort_values("event_timestamp")

    event_records = timeline.to_dict(orient="records")

    # Convert values into JSON-safe Python values.
    evidence = {
        "transaction_id": transaction.get("transaction_id"),
        "customer_id": transaction.get("customer_id"),
        "merchant_id": transaction.get("merchant_id"),
        "merchant_category": transaction.get("merchant_category"),
        "provider": transaction.get("provider"),
        "bank": transaction.get("bank"),
        "payment_method": transaction.get("payment_method"),
        "currency": transaction.get("currency"),
        "amount": transaction.get("amount"),
        "created_at": transaction.get("created_at"),
        "status": transaction.get("status"),

        "event_count": len(event_records),

        "events": event_records,

        "reconciliation_status": anomaly.get(
            "reconciliation_status"
        ),

        "incident_type": anomaly.get(
            "incident_type"
        ),

        "incident_category": anomaly.get(
            "incident_category"
        ),

        "priority": anomaly.get(
            "priority"
        ),

        "recommended_owner": anomaly.get(
            "recommended_owner"
        ),

        "recommended_action": anomaly.get(
            "recommended_action"
        ),

        "anomaly_prediction": anomaly.get(
            "anomaly_prediction"
        ),

        "anomaly_score": anomaly.get(
            "anomaly_score"
        ),

        "anomaly_level": anomaly.get(
            "anomaly_level"
        ),

        "potential_duplicate": anomaly.get(
            "potential_duplicate"
        ),
    }

    return evidence


# =========================================================
# AI PROMPT
# =========================================================

def build_prompt(evidence):
    """
    Build an evidence-first investigation prompt.

    The model is explicitly instructed not to invent facts
    or interpret event count as retry/attempt count.
    """

    evidence_json = json.dumps(
        evidence,
        indent=2,
        default=str,
    )

    return f"""
You are an evidence-first payment operations investigation assistant.

Your job is to explain what the available PayResolve data shows
about ONE payment transaction.

IMPORTANT RULES:

1. Use ONLY the evidence provided below.
2. Do not invent facts.
3. Do not assume facts that are not explicitly present.
4. Do not infer that event_count represents the number of payment
   attempts, retries, or customer actions.
5. "event_count" means only the number of payment events recorded
   in the available event data.
6. If something cannot be determined from the evidence, explicitly
   state that it is unknown.
7. Do not claim that a customer was debited unless the evidence
   explicitly contains a debit event or debit field.
8. Do not claim that money was settled unless the evidence contains
   a settlement event or settlement evidence.
9. Do not diagnose fraud.
10. Do not make autonomous financial decisions.
11. Recommended next steps must be operational investigation steps,
    not financial decisions.

Use exactly these sections:

INVESTIGATION SUMMARY

Briefly explain the current state of the transaction using only
the evidence.

EVIDENCE

List the most important factual observations.

WHAT IS UNKNOWN

Clearly identify information that the available data does not
establish.

RECOMMENDED NEXT STEP

Give the most appropriate operational investigation step based
on the available evidence.

TRANSACTION EVIDENCE

Briefly restate the key transaction facts.

PAYRESOLVE EVIDENCE:

{evidence_json}
"""


# =========================================================
# GENERATE AI EXPLANATION
# =========================================================

def generate_ai_explanation(transaction_id):
    """
    Generate an AI investigation for one transaction.

    Returns
    -------
    str
        AI-generated investigation.
    """

    evidence = build_transaction_evidence(transaction_id)

    client = get_groq_client()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=600,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful payment operations analyst. "
                    "You must distinguish facts from unknowns and "
                    "never invent transaction details."
                ),
            },
            {
                "role": "user",
                "content": build_prompt(evidence),
            },
        ],
    )

    explanation = response.choices[0].message.content.strip()

    return explanation


# =========================================================
# SAVE EXPLANATION
# =========================================================

def save_ai_explanation(transaction_id, explanation):
    """
    Save or update the AI explanation for a transaction.
    """

    if OUTPUT_FILE.exists():
        existing_df = pd.read_csv(OUTPUT_FILE)
    else:
        existing_df = pd.DataFrame(
            columns=[
                "transaction_id",
                "ai_explanation",
            ]
        )

    existing_df = existing_df[
        existing_df["transaction_id"].astype(str)
        != str(transaction_id)
    ]

    new_record = pd.DataFrame(
        [
            {
                "transaction_id": transaction_id,
                "ai_explanation": explanation,
            }
        ]
    )

    updated_df = pd.concat(
        [
            existing_df,
            new_record,
        ],
        ignore_index=True,
    )

    updated_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )


# =========================================================
# SINGLE TRANSACTION PIPELINE
# =========================================================

def investigate_transaction(transaction_id):
    """
    Generate and persist an AI investigation for one transaction.
    """

    print(
        f"Generating AI investigation for {transaction_id}..."
    )

    explanation = generate_ai_explanation(
        transaction_id
    )

    save_ai_explanation(
        transaction_id,
        explanation,
    )

    print(
        f"AI investigation saved for {transaction_id}."
    )

    return explanation


# =========================================================
# DEVELOPMENT BATCH MODE
# =========================================================

def main():
    """
    Generate AI explanations for a small number of anomalous
    transactions during development.

    This is intentionally limited to avoid unnecessary API usage.
    """

    if not ANOMALY_FILE.exists():
        raise FileNotFoundError(
            f"Anomaly results not found: {ANOMALY_FILE}"
        )

    anomaly_df = pd.read_csv(
        ANOMALY_FILE
    )

    anomaly_df = anomaly_df.sort_values(
        "anomaly_score",
        ascending=False,
    )

    limit = 5

    selected = anomaly_df.head(limit)

    print("Groq connection established.")
    print(
        f"Generating AI explanations for "
        f"{len(selected)} transaction(s)..."
    )

    for _, row in selected.iterrows():

        transaction_id = row["transaction_id"]
        incident_type = row.get(
            "incident_type",
            "UNKNOWN",
        )

        print(
            f"  → {transaction_id} "
            f"({incident_type})"
        )

        try:
            investigate_transaction(
                transaction_id
            )

        except Exception as error:
            print(
                f"  ! Failed for {transaction_id}: "
                f"{error}"
            )

    print(
        f"\nResults saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()