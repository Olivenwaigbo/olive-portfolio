import pandas as pd
import pytest

from src.anomaly_detection import detect_anomalies


@pytest.fixture(scope="module")
def anomaly_results():
    """
    Run anomaly detection once for the entire test module.
    """

    return detect_anomalies()


def test_anomaly_detection_returns_dataframe(anomaly_results):
    assert isinstance(anomaly_results, pd.DataFrame)


def test_anomaly_detection_contains_required_columns(anomaly_results):
    required_columns = [
        "transaction_id",
        "anomaly_prediction",
        "anomaly_score",
        "anomaly_level",
        "anomaly_reason",
    ]

    for column in required_columns:
        assert column in anomaly_results.columns


def test_anomaly_predictions_are_valid(anomaly_results):
    valid_predictions = {
        "ANOMALY",
        "NORMAL",
    }

    assert set(
        anomaly_results["anomaly_prediction"].dropna().unique()
    ).issubset(valid_predictions)


def test_anomaly_levels_are_valid(anomaly_results):
    valid_levels = {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    assert set(
        anomaly_results["anomaly_level"].dropna().unique()
    ).issubset(valid_levels)


def test_anomaly_scores_are_between_zero_and_one_hundred(
    anomaly_results
):
    assert anomaly_results["anomaly_score"].min() >= 0
    assert anomaly_results["anomaly_score"].max() <= 100


def test_anomalies_are_detected(anomaly_results):
    anomalies = anomaly_results[
        anomaly_results["anomaly_prediction"] == "ANOMALY"
    ]

    assert len(anomalies) > 0