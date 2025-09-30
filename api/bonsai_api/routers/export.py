from functools import lru_cache
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import PlainTextResponse

from bonsai_api.crud.sample import EntryNotFound, get_sample
from bonsai_api.db import Database
from bonsai_api.dependencies import get_current_active_user, get_database
from bonsai_api.models.user import UserOutputDatabase
from bonsai_api.lims_export.models import AssayConfig
from bonsai_api.lims_export.export import lims_rs_formatter, serialize_lims_results
from bonsai_api.lims_export.config import InvalidFormatError, load_export_config
from bonsai_api.config import settings
from .shared import SAMPLE_ID_PATH

LOG = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TAGS = [
    "export",
]
READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"
UPDATE_PERMISSION = "samples:update"



@lru_cache(maxsize=1)
def _load_lims_config_map() -> dict[str, AssayConfig]:
    """
    Load and cache LIMS export configuration, keyed by assay.

    Returns:
        dict: {assay: AssayConfig}
    """
    conf_list = load_export_config(settings.lims_export_config)
    config_map: dict[str, AssayConfig] = {}
    for cnf in conf_list:
        if cnf.assay in config_map:
            LOG.warning(
                "Duplicate assay key in LIMS export config; last one wins",
                extra={"assay": cnf.assay}
            )
        config_map[cnf.assay] = cnf
    LOG.info("LIMS export config loaded", extra={"assay_count": len(config_map)})
    return config_map



@router.get(
    "/export/{sample_id}/lims", response_class=PlainTextResponse, tags=DEFAULT_TAGS,
    summary="Export a sample to a LIMS-compatible file.",
    response_description="Result in TSV (default) or CSV for ingestion by a LIMS.",
    responses={
        200: {
            "content": {
                "text/tab-separated-values": {},
                "text/csv": {},
                "text/plain": {},  # fallback
            }
        },
        404: {"description": "Sample not found"},
        422: {"description": "Sample is missing assay or export unsupported for its assay"},
        500: {"description": "Server error during LIMS export"},
        501: {"description": "LIMS formatter not implemented"},
    }
)
async def export_to_lims(
    sample_id: str = SAMPLE_ID_PATH,
    fmt: Literal["tsv", "csv"] = "tsv",
    db: Database = Depends(get_database),
    current_user: UserOutputDatabase = Security(  # pylint: disable=unused-argument
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    """Export a sample to a LIMS compatible file."""
    # 1. Get sample
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    # 2. Load configuration and format data
    assay = sample_obj.pipeline.assay
    try:
        config_map = _load_lims_config_map()
        conf = config_map.get(assay)
        if conf is None:
            LOG.info("No LIMS config for assay '%s'", assay, extra={"sample_id": sample_id})
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Export not supported for assay '{assay}'"
            )
        # Convert sample info to LIMS format
        lims_data = lims_rs_formatter(sample_obj, conf)
    except NotImplementedError as exc:
        LOG.exception(
            "LIMS formatter not implemented for this assay",
            extra={"sample_id": sample_id, "assay": assay}
        )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"LIMS export not implemented for assay '{assay}'",
        ) from exc
    except FileNotFoundError as exc:
        LOG.exception(
            "LIMS export configuration file missing/unreadable",
            extra={"config": settings.lims_export_config}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LIMS export configuration is missing or unreadable.",
        ) from exc
    except (InvalidFormatError, ValueError) as exc:
        LOG.exception(
            "Failed to format LIMS export",
            extra={"sample_id": sample_id, "assay": assay}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to format LIMS export.",
        ) from exc

    # 3. Serialize output data to correct media type
    if fmt == "tsv":
        media_type = "text/tab-separated-values; charset=utf-8"
        ext = "tsv"
    else:
        media_type = "text/csv; charset=utf-8"
        ext = "csv"
    body = serialize_lims_results(lims_data, delimiter=fmt)

    filename = f"{sample_obj.sample_id}_lims.{ext}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(content=body, media_type=media_type, headers=headers)
