"""Functions for performing CURD operations on sample collection."""
import logging
from bson.objectid import ObjectId
from ..db import Database
from ..models.sample import SampleInPipelineInput, SampleInCreate, SampleInDatabase
from typing import Dict, Any, List

LOG = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 1


async def create_sample(db: Database, sample: SampleInPipelineInput) -> SampleInDatabase:
    """Create a new sample document in database from structured input."""
    # restructure data to db format

    # validate data format
    sample_db_fmt: SampleInCreate = SampleInCreate(
        sample_id=sample.sample_id,
        schema_version=CURRENT_SCHEMA_VERSION,
        in_collections=[],
        run_metadata=sample.run_metadata,
        qc=sample.qc,
        species_prediction=sample.species_prediction,
        add_typing_result=[
            {"type": "cgmlst", "result": sample.mlst},
            {"type": "cgmlst", "result": sample.cgmlst},
        ],
        add_phenotype_prediction=[
            {"type": "antimicrobial_resistance", "result": sample.antimicrobial_resistance},
            {"type": "chemical_resistance", "result": sample.chemical_resistance},
            {"type": "environmental_factor_resistance", "result": sample.environmental_resistance},
            {"type": "virulence", "result": sample.virulence},
        ],
    )
    # store data in database
    doc = await db.sample_collection.insert_one(
        sample_db_fmt.dict(by_alias=True)
    )
    #print(sample_db_fmt.dict(by_alias=True))

    # create object representing the dataformat in database
    inserted_id = doc.inserted_id
    db_obj = SampleInDatabase(
        id=str(inserted_id),
        created_at=ObjectId(inserted_id).generation_time,
        modified_at=ObjectId(inserted_id).generation_time,
        **sample_db_fmt.dict(by_alias=True)
    )
    return db_obj