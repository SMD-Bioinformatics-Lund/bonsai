"""File handling operations for samples (alignment, VCF, signatures)."""

import logging
from typing import cast

from bonsai_api.db import Database
from bonsai_api.dependencies import (
    get_current_active_user,
    get_database,
)
from bonsai_api.models.enums import ClusterMethod, TypingMethod
from bonsai_api.models.sample import InputSearchSimilar
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.redis.minhash import (
    schedule_find_similar_and_cluster,
    schedule_find_similar_samples,
)
from bonsai_api.redis.models import SubmittedJob
from bonsai_api.services.sample_service import (
    add_ska_index_service,
    add_sourmash_index_service,
)
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Security,
    status,
)

LOG = logging.getLogger(__name__)
router = APIRouter()

from .permissions import READ_PERMISSION


def parse_signature_json(signature: str = Body(..., embed=True)) -> dict:
    """Parse and validate signature JSON."""
    import json

    try:
        return json.loads(signature)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON in signature: {str(e)}",
        ) from e


@router.post("/samples/{sample_id}/signature")
async def create_genome_signatures_sample(
    sample_id: str = Path(...),
    signature: str = Depends(parse_signature_json),
    db: Database = Depends(get_database),
) -> dict[str, str]:
    """Entrypoint for uploading a genome signature to the database."""

    job_ids = await add_sourmash_index_service(
        db, sample_id=sample_id, sketch=signature
    )
    return {
        "id": sample_id,
        "add_signature_job": job_ids["add_sketch_job"],
        "index_job": job_ids["index_job"],
    }


@router.post("/samples/{sample_id}/ska_index")
async def add_ska_index_to_sample(
    sample_id: str = Path(...),
    index: str = Body(..., embed=True),
    force: bool = Body(False, embed=True),
    db: Database = Depends(get_database),
) -> dict[str, str]:
    """Entrypoint for associating a SKA index with the sample."""
    await add_ska_index_service(db, sample_id=sample_id, index_uri=index, force=force)

    return {"sample_id": sample_id, "index_file": index}


@router.post(
    "/samples/{sample_id}/similar",
    response_model=SubmittedJob,
    status_code=status.HTTP_202_ACCEPTED,
)
async def find_similar_samples(
    body: InputSearchSimilar,
    sample_id: str = Path(...),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
) -> SubmittedJob:
    """Find similar samples using minhash distance.

    The entrypoint adds a similarity search job to the redis queue.
    """
    LOG.info("ref: %s, body: %s, cluster: %s", sample_id, body, body.cluster)
    try:
        if body.cluster:
            typing_method = cast(TypingMethod, body.typing_method)
            cluster_method = cast(ClusterMethod, body.cluster_method)
            submission_info: SubmittedJob = schedule_find_similar_and_cluster(
                sample_id,
                min_similarity=body.similarity,
                limit=body.limit,
                narrow_to_sample_ids=body.narrow_to_sample_ids,
                typing_method=typing_method,
                cluster_method=cluster_method,
            )
        else:
            submission_info: SubmittedJob = schedule_find_similar_samples(
                sample_id,
                min_similarity=body.similarity,
                limit=body.limit,
                narrow_to_sample_ids=body.narrow_to_sample_ids,
            )
    except ConnectionError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
        ) from error
    return submission_info
