from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "incident_classification_results.csv"
OUTPUT_FILE = DATA_DIR / "anomaly_detection_results.csv"


def detect_anomalies():
    """
    Detect unusual payment transactions using Isolation Forest.

    Returns:
        pandas.DataFrame: Transaction-level anomaly results.
    """

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Incident classification dataset not found: {INPUT_FILE}"
        )

    df = pd.read_csv(INPUT_FILE)

    # ---------------------------------------------------------
    # Prepare machine-learning features
    # ---------------------------------------------------------

    feature_columns = [
        "amount",
        "event_count",
        "has_success",
        "has_settlement",
        "has_reversal",
        "has_failure",
        "has_pending",
        "has_timeout",
        "has_debit",
        "potential_duplicate",
    ]

    missing_columns = [
        column
        for column in feature_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required anomaly detection columns: "
            + ", ".join(missing_columns)
        )

    features = df[feature_columns].copy()

    boolean_columns = [
        "has_success",
        "has_settlement",
        "has_reversal",
        "has_failure",
        "has_pending",
        "has_timeout",
        "has_debit",
        "potential_duplicate",
    ]

    for column in boolean_columns:
        features[column] = (
            features[column]
            .fillna(False)
            .astype(int)
        )

    features["amount"] = pd.to_numeric(
        features["amount"],
        errors="coerce",
    ).fillna(0)

    features["event_count"] = pd.to_numeric(
        features["event_count"],
        errors="coerce",
    ).fillna(0)

    # ---------------------------------------------------------
    # Train Isolation Forest
    # ---------------------------------------------------------

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )

    predictions = model.fit_predict(features)

    raw_scores = model.decision_function(features)

    # ---------------------------------------------------------
    # Convert model output
    # ---------------------------------------------------------

    df["anomaly_prediction"] = [
        "ANOMALY" if prediction == -1 else "NORMAL"
        for prediction in predictions
    ]

    # Lower Isolation Forest decision scores indicate
    # more unusual observations.
    min_score = raw_scores.min()
    max_score = raw_scores.max()

    if max_score == min_score:
        normalized_scores = [0.0] * len(raw_scores)
    else:
        normalized_scores = (
            (max_score - raw_scores)
            / (max_score - min_score)
        ) * 100

    df["anomaly_score"] = normalized_scores

    # ---------------------------------------------------------
    # Anomaly levels
    # ---------------------------------------------------------

    def get_anomaly_level(score):
        if score >= 80:
            return "HIGH"
        elif score >= 50:
            return "MEDIUM"
        return "LOW"

    df["anomaly_level"] = df["anomaly_score"].apply(
        get_anomaly_level
    )

    # ---------------------------------------------------------
    # Build evidence-based anomaly reason
    # ---------------------------------------------------------

    amount_95th_percentile = df["amount"].quantile(0.95)

    def build_reason(row):
        reasons = []

        if row["has_timeout"]:
            reasons.append("provider timeout")

        if row["has_debit"] and not row["has_settlement"]:
            reasons.append("debit without settlement")

        if row["potential_duplicate"]:
            reasons.append("potential duplicate")

        if row["status"] == "FAILED" and row["has_success"]:
            reasons.append("status conflict")

        if row["status"] == "REVERSED" and not row["has_reversal"]:
            reasons.append("missing reversal")

        if row["status"] == "PENDING" and not row["has_pending"]:
            reasons.append("missing pending event")

        if row["event_count"] == 0:
            reasons.append("missing payment events")

        if row["amount"] >= amount_95th_percentile:
            reasons.append("high transaction amount")

        if not reasons:
            reasons.append("unusual transaction pattern")

        return "; ".join(reasons)

    df["anomaly_reason"] = df.apply(
        build_reason,
        axis=1,
    )

    # ---------------------------------------------------------
    # Save results
    # ---------------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return df


def main():
    result = detect_anomalies()

    anomalies = result[
        result["anomaly_prediction"] == "ANOMALY"
    ]

    print(f"Total transactions: {len(result):,}")
    print(f"Detected anomalies: {len(anomalies):,}")
    print(
        f"Normal transactions: "
        f"{len(result) - len(anomalies):,}"
    )

    print("\nAnomaly levels:")
    print(result["anomaly_level"].value_counts())

    print("\nIncident types among detected anomalies:")
    print(
        anomalies["incident_type"].value_counts()
    )

    print("\nHighest anomaly scores:")

    highest_risk = (
        result.sort_values(
            "anomaly_score",
            ascending=False,
        )
        .head(10)
    )

    columns_to_show = [
        "transaction_id",
        "amount",
        "provider",
        "status",
        "incident_type",
        "anomaly_score",
        "anomaly_level",
    ]

    print(
        highest_risk[columns_to_show].to_string(
            index=False
        )
    )

    print(
        f"\nResults saved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()