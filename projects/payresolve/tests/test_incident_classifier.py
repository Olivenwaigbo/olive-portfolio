import pandas as pd
import pytest

from src.reconciliation import reconcile_transactions
from src.incident_classifier import classify_incidents


@pytest.fixture(scope="module")
def classified_results():
    """
    Run reconciliation and classification once for the
    entire test module.
    """

    reconciliation_result = reconcile_transactions()

    return classify_incidents(reconciliation_result)


def test_classifier_returns_dataframe(classified_results):
    assert isinstance(classified_results, pd.DataFrame)


def test_classifier_contains_required_columns(classified_results):
    required_columns = [
        "transaction_id",
        "incident_type",
        "incident_category",
        "priority",
        "recommended_owner",
        "recommended_action",
    ]

    for column in required_columns:
        assert column in classified_results.columns


def test_provider_timeout_is_classified_correctly(classified_results):
    timeout_records = classified_results[
        classified_results["incident_type"] == "PROVIDER_TIMEOUT"
    ]

    assert len(timeout_records) > 0

    assert (
        timeout_records["incident_category"]
        == "PROVIDER_CONNECTIVITY"
    ).all()


def test_settlement_incidents_are_classified(classified_results):
    settlement_incidents = classified_results[
        classified_results["incident_type"].isin(
            [
                "MISSING_SETTLEMENT",
                "DEBIT_WITHOUT_SETTLEMENT",
                "MISSING_REVERSAL",
            ]
        )
    ]

    assert len(settlement_incidents) > 0

    assert (
        settlement_incidents["incident_category"]
        == "SETTLEMENT_RECONCILIATION"
    ).all()


def test_priorities_are_valid(classified_results):
    valid_priorities = {
        "P1",
        "P2",
        "P3",
        "NONE",
    }

    assert set(
        classified_results["priority"].dropna().unique()
    ).issubset(valid_priorities)