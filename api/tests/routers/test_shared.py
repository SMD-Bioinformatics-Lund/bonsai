"""Test functions in routers/shared.py"""

import asyncio
import gzip
import json
from tempfile import SpooledTemporaryFile

import pytest
from fastapi import UploadFile

from bonsai_api.models.qc import QcClassification, SampleQcClassification
from bonsai_api.routers.shared import (
    action_from_qc_classification,
    parse_signature_json,
)

qc_unprocessed = QcClassification(status=SampleQcClassification.UNPROCESSED)
qc_passed = QcClassification(status=SampleQcClassification.PASSED)
qc_failed = QcClassification(status=SampleQcClassification.FAILED)


@pytest.mark.parametrize(
    "status,exp_action",
    [
        (qc_unprocessed, "include"),
        (qc_passed, "include"),
        (qc_failed, "exclude"),
    ],
)
def test_action_from_qc_classification(status: QcClassification, exp_action: str):
    """Test that the correct actions are taken.

    UPROCESSED -> include
    PASSED -> include
    FAILED -> exclude
    """

    action = action_from_qc_classification(status)
    assert action == exp_action


@pytest.mark.parametrize("compress", [False, True])
def test_parse_signature_json_returns_json_text(compress: bool):
    """MinHash workers receive JSON text for plain and gzipped signatures."""
    signature = [{"name": "synthetic", "signatures": [{"mins": [1, 2, 3]}]}]
    raw = json.dumps(signature).encode("utf-8")
    if compress:
        raw = gzip.compress(raw)

    upload_file = SpooledTemporaryFile()
    upload_file.write(raw)
    upload_file.seek(0)
    upload = UploadFile(file=upload_file, filename="synthetic.sig")
    parsed = asyncio.run(parse_signature_json(upload))

    assert isinstance(parsed, str)
    assert json.loads(parsed) == signature
