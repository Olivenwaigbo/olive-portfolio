from pathlib import Path
import json

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.ai_explainer import investigate_transaction


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# ============================================================
# FILES
# ============================================================

TRANSACTIONS_FILE = DATA_DIR / "transactions_test.csv"
EVENTS_FILE = DATA_DIR / "events_test.csv"
RECONCILIATION_FILE = DATA_DIR / "reconciliation_test_results.csv"
INCIDENT_FILE = DATA_DIR / "incident_classification_results.csv"
ANOMALY_FILE = DATA_DIR / "anomaly_detection_results.csv"
AI_FILE = DATA_DIR / "ai_explanations.csv"


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="PayResolve API",
    description="Payment Operations Intelligence API",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HELPERS
# ============================================================

def dataframe_to_records(df: pd.DataFrame):
    """
    Convert a pandas DataFrame into JSON-safe records.

    Using pandas to_json handles timestamps and other
    pandas-specific data types safely.
    """

    json_string = df.to_json(
        orient="records",
        date_format="iso",
    )

    return json.loads(json_string)


def load_transactions():
    if not TRANSACTIONS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Transactions dataset not found.",
        )

    return pd.read_csv(TRANSACTIONS_FILE)


def load_events():
    if not EVENTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Payment events dataset not found.",
        )

    return pd.read_csv(EVENTS_FILE)


def load_reconciliation():
    if not RECONCILIATION_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Reconciliation results not found.",
        )

    return pd.read_csv(RECONCILIATION_FILE)


def load_incidents():
    if not INCIDENT_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Incident classification results not found.",
        )

    return pd.read_csv(INCIDENT_FILE)


def load_anomalies():
    if not ANOMALY_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Anomaly detection results not found.",
        )

    return pd.read_csv(ANOMALY_FILE)


def load_ai_explanations():
    if not AI_FILE.exists():
        return pd.DataFrame()

    return pd.read_csv(AI_FILE)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "name": "PayResolve API",
        "description": "Payment Operations Intelligence API",
        "status": "running",
        "version": "1.0.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "payresolve-api",
    }


# ============================================================
# SUMMARY
# ============================================================

@app.get("/summary")
def summary():
    transactions = load_transactions()
    reconciliation = load_reconciliation()
    anomalies = load_anomalies()

    total_transactions = len(transactions)

    successful_transactions = len(
        transactions[
            transactions["status"].astype(str).str.upper() == "SUCCESS"
        ]
    )

    reconciliation_exceptions = len(
        reconciliation[
            reconciliation["reconciliation_status"].astype(str).str.upper()
            == "EXCEPTION"
        ]
    )

    detected_anomalies = len(
        anomalies[
            anomalies["anomaly_prediction"].astype(str).str.upper()
            == "ANOMALY"
        ]
    )

    success_rate = (
        successful_transactions / total_transactions * 100
        if total_transactions > 0
        else 0
    )

    return {
        "total_transactions": total_transactions,
        "successful_transactions": successful_transactions,
        "success_rate": round(success_rate, 2),
        "reconciliation_exceptions": reconciliation_exceptions,
        "detected_anomalies": detected_anomalies,
    }


# ============================================================
# TRANSACTIONS
# ============================================================

@app.get("/transactions")
def get_transactions(
    status: str | None = None,
    provider: str | None = None,
    incident_type: str | None = None,
    limit: int = 500,
):
    transactions = load_transactions()
    reconciliation = load_reconciliation()
    incidents = load_incidents()
    anomalies = load_anomalies()
    ai_explanations = load_ai_explanations()

    # --------------------------------------------------------
    # Merge reconciliation information
    # --------------------------------------------------------

    reconciliation_columns = [
        "transaction_id",
        "reconciliation_status",
        "incident_type",
    ]

    available_reconciliation_columns = [
        column
        for column in reconciliation_columns
        if column in reconciliation.columns
    ]

    reconciliation_data = reconciliation[
        available_reconciliation_columns
    ].copy()

    transactions = transactions.merge(
        reconciliation_data,
        on="transaction_id",
        how="left",
        suffixes=("", "_reconciliation"),
    )

    # --------------------------------------------------------
    # Merge incident classification
    # --------------------------------------------------------

    incident_columns = [
        "transaction_id",
        "incident_category",
        "priority",
        "recommended_owner",
        "recommended_action",
    ]

    available_incident_columns = [
        column
        for column in incident_columns
        if column in incidents.columns
    ]

    incident_data = incidents[
        available_incident_columns
    ].copy()

    transactions = transactions.merge(
        incident_data,
        on="transaction_id",
        how="left",
    )

    # --------------------------------------------------------
    # Merge anomaly information
    # --------------------------------------------------------

    anomaly_columns = [
        "transaction_id",
        "anomaly_prediction",
        "anomaly_score",
        "anomaly_level",
        "potential_duplicate",
        "anomaly_reason",
    ]

    available_anomaly_columns = [
        column
        for column in anomaly_columns
        if column in anomalies.columns
    ]

    anomaly_data = anomalies[
        available_anomaly_columns
    ].copy()

    transactions = transactions.merge(
        anomaly_data,
        on="transaction_id",
        how="left",
    )

    # --------------------------------------------------------
    # Merge AI explanations
    # --------------------------------------------------------

    if not ai_explanations.empty:
        ai_columns = [
            "transaction_id",
            "ai_explanation",
        ]

        available_ai_columns = [
            column
            for column in ai_columns
            if column in ai_explanations.columns
        ]

        if available_ai_columns:
            ai_data = ai_explanations[
                available_ai_columns
            ].copy()

            transactions = transactions.merge(
                ai_data,
                on="transaction_id",
                how="left",
            )

    # --------------------------------------------------------
    # Filters
    # --------------------------------------------------------

    if status:
        transactions = transactions[
            transactions["status"].astype(str).str.upper()
            == status.upper()
        ]

    if provider:
        transactions = transactions[
            transactions["provider"].astype(str).str.upper()
            == provider.upper()
        ]

    if incident_type:
        transactions = transactions[
            transactions["incident_type"].astype(str).str.upper()
            == incident_type.upper()
        ]

    # --------------------------------------------------------
    # Limit
    # --------------------------------------------------------

    transactions = transactions.head(limit)

    return {
        "count": len(transactions),
        "transactions": dataframe_to_records(transactions),
    }


# ============================================================
# SINGLE TRANSACTION
# ============================================================

@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    transactions = load_transactions()
    reconciliation = load_reconciliation()
    incidents = load_incidents()
    anomalies = load_anomalies()
    ai_explanations = load_ai_explanations()

    # --------------------------------------------------------
    # Find transaction
    # --------------------------------------------------------

    match = transactions[
        transactions["transaction_id"] == transaction_id
    ].copy()

    if match.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found.",
        )

    # --------------------------------------------------------
    # Reconciliation
    # --------------------------------------------------------

    reconciliation_match = reconciliation[
        reconciliation["transaction_id"] == transaction_id
    ]

    if not reconciliation_match.empty:
        reconciliation_record = reconciliation_match.iloc[0]

        for column in [
            "reconciliation_status",
            "incident_type",
        ]:
            if column in reconciliation_record:
                match[column] = reconciliation_record[column]

    # --------------------------------------------------------
    # Incident classification
    # --------------------------------------------------------

    incident_match = incidents[
        incidents["transaction_id"] == transaction_id
    ]

    if not incident_match.empty:
        incident_record = incident_match.iloc[0]

        for column in [
            "incident_category",
            "priority",
            "recommended_owner",
            "recommended_action",
        ]:
            if column in incident_record:
                match[column] = incident_record[column]

    # --------------------------------------------------------
    # Anomaly detection
    # --------------------------------------------------------

    anomaly_match = anomalies[
        anomalies["transaction_id"] == transaction_id
    ]

    if not anomaly_match.empty:
        anomaly_record = anomaly_match.iloc[0]

        for column in [
            "anomaly_prediction",
            "anomaly_score",
            "anomaly_level",
            "potential_duplicate",
            "anomaly_reason",
        ]:
            if column in anomaly_record:
                match[column] = anomaly_record[column]

    # --------------------------------------------------------
    # AI explanation
    # --------------------------------------------------------

    if not ai_explanations.empty:
        ai_match = ai_explanations[
            ai_explanations["transaction_id"] == transaction_id
        ]

        if not ai_match.empty and "ai_explanation" in ai_match.columns:
            match["ai_explanation"] = ai_match.iloc[0][
                "ai_explanation"
            ]

    # --------------------------------------------------------
    # Return transaction
    # --------------------------------------------------------

    record = dataframe_to_records(match)[0]

    return record


# ============================================================
# TRANSACTION TIMELINE
# ============================================================

@app.get("/transactions/{transaction_id}/timeline")
def transaction_timeline(transaction_id: str):
    events_df = load_events()

    match = events_df[
        events_df["transaction_id"] == transaction_id
    ].copy()

    if match.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No payment events found for {transaction_id}.",
        )

    match = match.sort_values("event_timestamp")

    records = dataframe_to_records(match)

    return {
        "transaction_id": transaction_id,
        "event_count": len(records),
        "timeline": records,
    }


# ============================================================
# ON-DEMAND AI INVESTIGATION
# ============================================================

@app.post("/transactions/{transaction_id}/ai-investigation")
def generate_transaction_ai_investigation(
    transaction_id: str,
):
    """
    Generate an evidence-based AI investigation for a
    specific transaction.

    The AI does not make financial decisions.
    It explains the evidence already available in PayResolve.
    """

    try:
        explanation = investigate_transaction(
            transaction_id
        )

        return {
            "transaction_id": transaction_id,
            "ai_explanation": explanation,
            "status": "generated",
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"AI investigation failed: {error}",
        )


# ============================================================
# INCIDENTS
# ============================================================

@app.get("/incidents")
def get_incidents(
    priority: str | None = None,
    incident_type: str | None = None,
    limit: int = 500,
):
    incidents = load_incidents()

    if priority:
        incidents = incidents[
            incidents["priority"].astype(str).str.upper()
            == priority.upper()
        ]

    if incident_type:
        incidents = incidents[
            incidents["incident_type"].astype(str).str.upper()
            == incident_type.upper()
        ]

    incidents = incidents.head(limit)

    return {
        "count": len(incidents),
        "incidents": dataframe_to_records(incidents),
    }


# ============================================================
# ANOMALIES
# ============================================================

@app.get("/anomalies")
def get_anomalies(
    level: str | None = None,
    limit: int = 500,
):
    anomalies = load_anomalies()

    if level:
        anomalies = anomalies[
            anomalies["anomaly_level"].astype(str).str.upper()
            == level.upper()
        ]

    anomalies = anomalies.head(limit)

    return {
        "count": len(anomalies),
        "anomalies": dataframe_to_records(anomalies),
    }