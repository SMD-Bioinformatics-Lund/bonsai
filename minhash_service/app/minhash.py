"""Operations on minhash signatures."""
import logging
import gzip
import pathlib
import sourmash
from typing import List
from app import config
import fasteners
from enum import Enum
from pydantic import BaseModel
from scipy.cluster import hierarchy
from scipy.spatial.distance import pdist


LOG = logging.getLogger(__name__)


class SimilarSignature(BaseModel):
    """Container for similar signature result"""

    sample_id: str
    similarity: float 


class ClusterMethod(str, Enum):
    """Index of methods for hierarchical clustering of samples."""

    SINGLE = "single"
    COMPLETE = "complete"
    AVERAGE = "average"
    NJ = "neighbor_joining"


SimilarSignatures = List[SimilarSignature]


def _get_sbt_index(check: bool = True) -> str:
    """Get sourmash SBT index file."""
    signature_dir = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    index_path = signature_dir.joinpath(f"genomes.sbt.zip")

    # Check if file exist
    if check:
        if not index_path.is_file():
            raise FileNotFoundError(f"Sourmash index does not exist: {index_path}")
    # Load index to memory
    return str(index_path)


def get_signature_path(sample_id: str, check=True) -> str:
    signature_dir = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    signature_path = signature_dir.joinpath(f"{sample_id}.sig")

    # Check if file exist
    if check:
        if not signature_path.is_file():
            raise FileNotFoundError(f"Signature file not found, {signature_path}")
    # Load index to memory
    return str(signature_path)


def _load_signature(sample_id: str):
    """Load signature to memory."""
    # read signature
    signature_path = get_signature_path(sample_id)
    kmer_sizes = config.SIGNATURE_KMER_SIZE
    loaded = sourmash.load_file_as_signatures(signature_path, ksize=kmer_sizes)

    # check that were signatures loaded with current kmer
    loaded = list(loaded)
    if not loaded:
        raise ValueError(
            f"No signatures, sample id: {sample_id}, ksize: {kmer_sizes}, {loaded}"
        )
    return loaded


def write_genome_signature_file(sample_id: str, signature) -> pathlib.Path:
    """
    Add genome signature to index.
    
    Create new index if none exist.
    """
    # get signature directory
    LOG.info(f'Adding signature file for {sample_id}')
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)
    # make db if signature db is not present
    if not signature_db.exists():
        signature_db.mkdir(parents=True, exist_ok=True)

    # Get signature path and check if it exists
    signature_file = get_signature_path(sample_id)

    # check if compressed and decompress data
    LOG.info('Check if signature is compressed')
    if signature[:2] == b"\x1f\x8b":
        LOG.debug("Decompressing gziped file")
        signature = gzip.decompress(signature)

    # save signature to file
    LOG.info("Writing genome signatures to file")
    try:
        with open(signature_file, "w") as out:
            print(signature.decode("utf-8"), file=out)
    except PermissionError:
        msg = f"Dont have permission to write file to disk, {signature_file}"
        LOG.error(msg)
        raise PermissionError(msg)

    return signature_file


def remove_genome_signature_file(sample_id: str) -> bool:
    """Remove an existing signature file from disk."""

    # get signature directory
    signature_db = pathlib.Path(config.GENOME_SIGNATURE_DIR)

    # get genome index
    sbt_filename = _get_sbt_index()

    # check that signature doesnt exist
    # Get signature path and check if it exists
    signature_file = get_signature_path(sample_id)

    # read signature
    signature = next(
        sourmash.signature.load_signatures(
            signature_file, ksize=config.SIGNATURE_KMER_SIZE
        )
    )

    # remove file
    pathlib.Path(signature_file).unlink()

    # remove signature to existing index
    sbt_filename = signature_db.joinpath("genomes.sbt.zip")
    if sbt_filename.is_file():
        LOG.debug("Append to existing file")
        tree = sourmash.load_file_as_index(str(sbt_filename))

        # add generated signature to bloom tree
        LOG.info("Adding genome signatures to index")
        leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
        tree.remove_many(leaf)

        try:
            tree.save(str(sbt_filename.resolve()))
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err
        return True
    LOG.info(f"Signature file: {signature_file} was removed")
    return False


def add_genome_signatures_to_index(sample_ids: List[str]) -> bool:
    """Add genome signature file to sourmash index"""

    genome_index = _get_sbt_index(check=False)
    sbt_lock_path = f"{genome_index}.lock"
    lock = fasteners.InterProcessLock(sbt_lock_path)
    LOG.debug("Using lock: {sbt_lock_path}")

    signatures = []
    for sample_id in sample_ids:
        signature = _load_signature(sample_id)
        signatures.append(signature[0])

    # add signature to existing index
    # acquire lock to append signatures to database
    LOG.debug(f"Attempt to acquire lock to append {len(signatures)} to index...")
    with lock:
        # check if index already exist
        try:
            index_path = _get_sbt_index()
            tree = sourmash.load_file_as_index(index_path)
        except FileNotFoundError:
            tree = sourmash.sbtmh.create_sbt_index()

        # add generated signature to bloom tree
        LOG.info(f"Adding {len(signatures)} genome signatures to index")
        for signature in signatures:
            leaf = sourmash.sbtmh.SigLeaf(signature.md5sum(), signature)
            tree.add_node(leaf)
        # save updated bloom tree
        try:
            index_path = _get_sbt_index(check=False)
            tree.save(index_path)
        except PermissionError as err:
            LOG.error("Dont have permission to write file to disk")
            raise err

    return True


def get_signatures_similar_to_reference(sample_id: str, min_similarity: float, limit: int | None = None) -> SimilarSignatures:
    """Get find samples that are similar to reference sample.

    min_similarity - minimum similarity score to be included
    """

    # load sourmash index
    LOG.debug(f'Getting samples similar to: {sample_id}')
    index_path: pathlib.Path = _get_sbt_index()
    LOG.debug(f'Load index file to memory')
    tree = sourmash.load_file_as_index(index_path)

    # load reference sequence
    query_signature = _load_signature(sample_id)
    if len(query_signature) == 0:
        raise ValueError(f"No signature in: {signature_file.name} with kmer size: {config.SIGNATURE_KMER_SIZE}")
    else:
        query_signature = query_signature[0]

    # query for similar sequences
    LOG.debug(f'Searching for signatures with similarity > {min_similarity}')
    result = tree.search(query_signature, threshold=min_similarity) # read sample information of similar samples 
    samples = []

    for itr_no, (similarity, found_sig, _) in enumerate(result, start=1):
        # read sample results
        signature_path = pathlib.Path(found_sig.filename)
        # extract sample id from sample name
        base_fname = signature_path.name[: -len(signature_path.suffix)]
        samples.append(SimilarSignature(sample_id=base_fname, similarity=similarity))

        # break iteration if limit is reached
        if isinstance(limit, int) and limit == itr_no:
            break
    return samples


def to_newick(node, newick, parentdist, leaf_names) -> str:
    """Convert hierarcical tree representation to newick format."""

    if node.is_leaf():
        return "%s:%.2f%s" % (leaf_names[node.id], parentdist - node.dist, newick)
    else:
        if len(newick) > 0:
            newick = "):%.2f%s" % (parentdist - node.dist, newick)
        else:
            newick = ");"
        newick = to_newick(node.get_left(), newick, node.dist, leaf_names)
        newick = to_newick(node.get_right(), f",{newick}", node.dist, leaf_names)
        newick = f"({newick}"
        return newick


def cluster_minhash_signatures(sample_ids: List[str], method: ClusterMethod):
    """Cluster multiple samples on their minhash signatures."""

    # load sequence signatures to memory
    siglist = []
    for sample_id in sample_ids:
        signature = _load_signature(sample_id)
        siglist.extend(signature)  # append to all signatures

    # create distance matrix
    similarity = sourmash.compare.compare_all_pairs(
        siglist, ignore_abundance=True, n_jobs=1, return_ani=False
    )
    # cluster on similarity matrix
    Z = hierarchy.linkage(similarity, method=method.value)
    tree = hierarchy.to_tree(Z, False)
    # creae newick tree
    labeltext = [str(item).replace(".fasta", "") for item in siglist]
    newick_tree = to_newick(tree, "", tree.dist, labeltext)
    return newick_tree