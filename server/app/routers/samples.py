from datetime import datetime
from typing import Dict, List, Union, Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query, Security, status, File, UploadFile
from pymongo.errors import DuplicateKeyError

from ..crud.sample import EntryNotFound, add_comment, add_location
from ..crud.sample import hide_comment as hide_comment_for_sample
from ..crud.sample import create_sample as create_sample_record
from ..crud.sample import get_sample, get_samples
from ..crud.user import get_current_active_user
from ..db import db
from ..models.location import LocationOutputDatabase
from ..models.sample import (
    SAMPLE_ID_PATTERN,
    Comment,
    CommentInDatabase,
    SampleInDatabase,
    PipelineResult,
)
from ..models.user import UserOutputDatabase
from app import config
import sourmash
import pathlib
from Bio.SeqIO.FastaIO import SimpleFastaParser
import gzip
import io
import logging

LOG = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_TAGS = [
    "samples",
]
READ_PERMISSION = "samples:read"
WRITE_PERMISSION = "samples:write"


@router.get("/samples/", tags=DEFAULT_TAGS)
async def read_samples(
    limit: int = Query(10, gt=-1),
    skip: int = Query(0, gt=-1),
    offset: int = Query(0, gt=-1),
    sid: List[str] | None = Query(None),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    # skip and offset function the same
    skip = max([offset, skip])
    db_obj = await get_samples(db, limit, skip, sid)
    return {"status": "success", "total": len(db_obj), "records": db_obj}


@router.post("/samples/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS)
async def create_sample(
    sample: PipelineResult,
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        db_obj = await create_sample_record(db, sample)
    except DuplicateKeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error.details["errmsg"],
        )
    return {"type": "success", "id": db_obj.id}


@router.get("/samples/{sample_id}", tags=DEFAULT_TAGS)
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    try:
        sample_obj = await get_sample(db, sample_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return sample_obj


@router.put("/samples/{sample_id}", tags=DEFAULT_TAGS)
async def update_sample(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    sample: Dict | PipelineResult = Body({}),
    location: Dict = Body({}, embed=True),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    return {"sample_id": sample_id, "sample": sample, "location": location}
    try:
        comment_obj = await add_location(db, sample_id, location_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return comment_obj


@router.post("/samples/{sample_id}/signature", tags=DEFAULT_TAGS)
async def create_genome_signatures_sample(
    sample_id: str,
    signature: Annotated[bytes, File()],
):
    # verify that sample are in database
    await get_sample(db, sample_id)

    # get signature directory
    signature_db = pathlib.Path('/data/signature_db')
    # make db if signature db is not present
    if not signature_db.exists():
        signature_db.mkdir(parents=True, exist_ok=True)

    # check that signature doesnt exist
    signature_file = signature_db.joinpath(f"{sample_id}.sig")
    if signature_file.is_file():
        #raise ValueError("Sample already exist")
        pass

    # check if compressed and decompress data
    if signature[:2] == b"\x1f\x8b":
        LOG.debug("Decompressing gziped file")
        signature = gzip.decompress(signature)

    # save signature to file
    LOG.info("Writing genome signatures to file")
    try:
        with open(signature_file, "w") as out:
            print(signature, file=out)
    except PermissionError:
        LOG.error("Dont have permission to write file to disk")
    
    # load signature to memory
    signature = next(sourmash.signature.load_signatures(signature_file, ksize=config.SIGNATURE_KMER_SIZE))
    
    # add signature to existing index
    sbt_filename = signature_db.joinpath('genomes.sbt.zip')
    if sbt_filename.is_file():
        LOG.debug("Append to existing file")
        tree = sourmash.load_file_as_index(str(sbt_filename))
    else:
        LOG.debug("Create new index file")
        tree = sourmash.sbtmh.create_sbt_index()
    # add generated signature to bloom tree
    LOG.info("Adding genome signatures to index")
    leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
    tree.add_node(leaf)
    # save updated bloom tree
    try:
        tree.save(str(sbt_filename))
    except PermissionError:
        LOG.error("Dont have permission to write file to disk")
    # create signatures
    return {
        "type": "success", "id": sample_id, 
        "index_file": sbt_filename, 
        "signature_file": signature_file, 
    }


@router.post(
    "/samples/{sample_id}/comment",
    response_model=List[CommentInDatabase],
    tags=DEFAULT_TAGS,
)
async def post_comment(
    comment: Comment,
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        comment_obj = await add_comment(db, sample_id, comment)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return comment_obj


@router.delete(
    "/samples/{sample_id}/comment/{comment_id}",
    response_model=List[CommentInDatabase],
    tags=DEFAULT_TAGS,
)
async def hide_comment(
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    comment_id: int = Path(..., title="ID of the comment to delete"),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    """Hide comment from sample."""
    try:
        comment_obj = await hide_comment_for_sample(db, sample_id, comment_id)
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return comment_obj


@router.put("/samples/{sample_id}/location", tags=[*DEFAULT_TAGS, "locations"])
async def update_location(
    location_id: str = Body(...),
    sample_id: str = Path(
        ...,
        title="ID of the sample to get",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[WRITE_PERMISSION]
    ),
):
    try:
        location_obj: LocationOutputDatabase = await add_location(
            db, sample_id, location_id
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )
    return location_obj


@router.get("/samples/{sample_id}/similar", tags=DEFAULT_TAGS)
async def read_sample(
    sample_id: str = Path(
        ...,
        title="ID of the refernece sample",
        min_length=3,
        max_length=100,
        regex=SAMPLE_ID_PATTERN,
    ),
    limit: int = Query(10, gt=-1, title="Limit the output to x samples"),
    similarity: int = Query(10, gt=0, title="Similarity threshold"),
    current_user: UserOutputDatabase = Security(
        get_current_active_user, scopes=[READ_PERMISSION]
    ),
):
    return {"sample_id": sample_id, "limit": limit, "similaryt": similarity}