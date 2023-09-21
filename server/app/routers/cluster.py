"""Entrypoints for starting clustering jobs."""
from fastapi import APIRouter, Query, Security, status, HTTPException, Body
from pydantic import constr, Field
from enum import Enum
from ..crud.user import get_current_active_user
from ..crud.sample import get_typing_profiles, TypingProfileOutput
from ..crud.errors import EntryNotFound
from ..models.user import UserOutputDatabase
from ..models.base import RWModel
from ..db import db
from ..internal.cluster import cluster_on_allele_profile, ClusterMethod, DistanceMethod

router = APIRouter()

DEFAULT_TAGS = [
    "cluster",
]
READ_PERMISSION = "cluster:read"
WRITE_PERMISSION = "cluster:write"


class TypingMethod(Enum):
    MLST = "mlst"
    CGMLST = "cgmlst"


class clusterInput(RWModel):
    sample_ids: list[str] = Field(..., min_length=2, alias="sampleIds")
    distance: DistanceMethod
    method: ClusterMethod

    class Config:
        use_enum_values = False


#    current_user: UserOutputDatabase = Security(
#        get_current_active_user, scopes=[WRITE_PERMISSION]
#    ),
@router.post(
    "/cluster/{typing_method}/", status_code=status.HTTP_201_CREATED, tags=DEFAULT_TAGS
)
async def cluster_samples(
    typing_method: TypingMethod,
    clusterInput: clusterInput,
):
    """Cluster samples on their cgmlst profile.

    In order to cluster the samples, all samples need to have a profile and be of the same specie.
    """
    try:
        profiles: TypingProfileOutput = await get_typing_profiles(
            db, clusterInput.sample_ids, typing_method.value
        )
    except EntryNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )

    newick_tree: str = cluster_on_allele_profile_grapetree_mstrees(profiles)
    # sanity check that all samples had the desired typing result in the database
    # newick_tree: str = cluster_on_allele_profile(
    #     profiles, clusterInput.method, clusterInput.distance
    # )
    # print(newick_tree)
    return newick_tree


def cluster_on_allele_profile_grapetree_mstrees(profiles: TypingProfileOutput) -> str:
    """
    Cluster samples on their cgmlst profile using grapetree MStreesV2.
    """
    import tempfile
    import csv
    import subprocess
    import os

    processed_profiles: list[dict] = []
    tsv_header = set()

    for sample in profiles:
        processed_profile: dict = sample.allele_profile(strip_errors=True)

        # Recode missing vals to "-"
        processed_profile = {
            key: "-" if value is None else value
            for key, value in processed_profile.items()
        }

        tsv_header.update(processed_profile.keys())

        # First char in header needs to be a '#'
        processed_profile["#sample"] = sample.sample_id
        processed_profiles.append(processed_profile)

    with tempfile.NamedTemporaryFile("w", delete=True) as tmp_alleles_tsv:
        tsv_header = list(tsv_header)
        tsv_header.insert(0, "#sample")
        writer = csv.DictWriter(
            tmp_alleles_tsv, tsv_header, restval="-", delimiter="\t"
        )
        writer.writeheader()
        writer.writerows(processed_profiles)

        # grapetree freaks out if binary not called from the same dir as input tsv:
        grapetree_output = subprocess.Popen(
            [
                "grapetree",
                "-p",
                os.path.basename(tmp_alleles_tsv.name),
                "-m",
                "MSTreeV2",
            ],
            stdout=subprocess.PIPE,
            cwd="/tmp",
        )
        stdout, _ = grapetree_output.communicate()

    newick_tree = stdout.decode("utf-8").rstrip()
    return newick_tree
