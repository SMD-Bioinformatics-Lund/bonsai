"""Test functions in routers/shared.py"""

import pytest

from bonsai_api.models.sample import QcClassification, SampleQcClassification
from bonsai_api.routers.shared import action_from_qc_classification

qc_unprocessed = QcClassification(status=SampleQcClassification.UNPROCESSED)
qc_passed = QcClassification(status=SampleQcClassification.PASSED)
qc_failed = QcClassification(status=SampleQcClassification.FAILED)

@pytest.mark.parametrize("status,exp_action", [
    (qc_unprocessed, "include"),
    (qc_passed, "include"),
    (qc_failed, "exclude"),
])
def test_action_from_qc_classification(status: QcClassification, exp_action: str):
    """Test that the correct actions are taken.
    
    UPROCESSED -> include
    PASSED -> include
    FAILED -> exclude
    """

    action = action_from_qc_classification(status)
    assert action == exp_action
