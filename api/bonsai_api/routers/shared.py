"""Resources shared by many routers."""

import gzip
import json
import logging
from typing import Literal
from fastapi import HTTPException, Path, File, UploadFile
from enum import StrEnum

from ..models.sample import SAMPLE_ID_PATTERN, QcClassification, SampleQcClassification

LOG = logging.getLogger(__name__)

async def parse_signature_json(signature: UploadFile = File()) -> str:
    """Parse submitted json file that is either compressed or in clear text."""
    head = await signature.read(2)
    await signature.seek(0)
    is_gzipped = head.startswith(b"\x1f\x8b")

    raw = await signature.read()
    await signature.close()

    if is_gzipped:
        try:
            raw = gzip.decompress(raw)
        except OSError:
            LOG.error("Invalid gzip file: %s", signature.filename)
            raise HTTPException(400, "Invalid gzip file")
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as err:
        raise HTTPException(400, "File is not valid UTF-8 JSON") from err
    return json.dumps(data)

SAMPLE_ID_PATH: str = Path(
    ...,
    title="ID of the sample to get",
    min_length=3,
    max_length=100,
    pattern=SAMPLE_ID_PATTERN,
)

class RouterTags(StrEnum):
    """Tag names for API routes."""

    SAMPLE = 'sample'
    GROUP = 'groups'
    META = 'metadata'
    USR = 'user'
    JOB = 'jobs'


Action = Literal['include', 'exclude']

def action_from_qc_classification(classification: QcClassification) -> Action:
    """Determine action from qc classification."""
    accepted = [SampleQcClassification.PASSED, SampleQcClassification.UNPROCESSED]
    if classification.status in accepted:
        return "include"
    if classification.status == SampleQcClassification.FAILED:
        return "exclude"
    return "exclude"
