import logging

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import PlainTextResponse

from bonsai_api.lims_export.export import load_export_config, lims_rs_formatter, serialize_lims_results
from bonsai_api.config import settings
from ..crud.sample import EntryNotFound, get_sample
from ..crud.user import get_current_active_user
from ..db import Database, get_db
from ..models.user import UserOutputDatabase
from .shared import SAMPLE_ID_PATH

LOG = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TAGS = [
    "export",
]
READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"


@router.get(
    "/export/{sample_id}/lims", response_class=PlainTextResponse, tags=DEFAULT_TAGS
)
async def export_to_lims(
    sample_id: str = SAMPLE_ID_PATH,
    db: Database = Depends(get_db),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Export a sample to a LIMS compatible file."""
    # get sample info
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    # convert sample data to LIMS format
    try:
        # load export config using file in settings
        cnf = load_export_config(settings.export_config)
        lims_data = lims_rs_formatter(sample_obj, cnf)
        tabular = serialize_lims_results(lims_data, delimiter="tsv")
    except NotImplementedError as error:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(error),
        ) from error

    # return data as file
    return tabular
