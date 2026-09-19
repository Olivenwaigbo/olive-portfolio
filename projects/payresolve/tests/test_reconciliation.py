import pandas as pd
import pytest

from src.reconciliation import reconcile_transactions


@pytest.fixture(scope="module")
def reconciliation_result():
    """
    Run reconciliation once for the entire test module.
    This prevents every test from rerunning the full pipeline.
    """
    return reconcile_transactions()


def test_reconciliation_returns_dataframe(reconciliation_result):
    assert isinstance(reconciliation_result, pd.DataFrame)


def test_reconciliation_contains_required_columns(reconciliation_result):
    required_columns = [
        "transaction_id",
        "reconciliation_status",
        "incident_type",
        "severity",
    ]

    for column in required_columns:
        assert column in reconciliation_result.columns


def test_reconciliation_detects_exceptions(reconciliation_result):
    exceptions = reconciliation_result[
        reconciliation_result["reconciliation_status"] == "EXCEPTION"
    ]

    assert len(exceptions) > 0


def test_reconciliation_detects_provider_timeout(reconciliation_result):
    timeouts = reconciliation_result[
        reconciliation_result["incident_type"] == "PROVIDER_TIMEOUT"
    ]

    assert len(timeouts) > 0


def test_reconciliation_detects_potential_duplicates(reconciliation_result):
    duplicates = reconciliation_result[
        reconciliation_result["incident_type"] == "POTENTIAL_DUPLICATE"
    ]

    assert len(duplicates) > 0