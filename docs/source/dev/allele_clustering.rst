Allele clustering service
=========================

The allele clustering service subscribes to the Redis database and listens for jobs on the `allele_clustering` queue. The exposed functions are located in `tasks.py`.

Tasks
-----

.. autofunction:: allele_cluster_service.tasks.cluster

Allele profile validation
-------------------------

The basket calls ``POST /cluster/validate`` to check MLST and cgMLST separately.
The affected menu option stays disabled until validation succeeds; MinHash and
SNV clustering do not depend on typing schemes. Submission repeats the same
validation, so browser checks cannot bypass the API rules.

MLST uses its declared scheme name. cgMLST uses a declared identity in the
result's ``scheme`` field or the analysis envelope's ``meta.scheme``. When the
analysis links to a pipeline run with exactly one ChewBBACA database, its name
and version are included in the identity. The selected analysis's own run is
used, rather than the latest run for an unrelated analysis. Legacy records
without a verifiable identity cannot be clustered until the missing scheme
provenance is supplied. Equal locus names alone are not proof of scheme identity.

Profiles must have matching scheme identities and complete locus sets, including
loci with missing calls. The API also rejects selections containing a pair of
otherwise callable profiles with no jointly called loci.

The API normalizes scalar calls while retaining numeric-string compatibility.
Null, ambiguous, partial, and unresolvable calls are missing data; allele zero is
also missing, matching the worker's convention. The exported TSV has a named
``sample_id`` index column and prefixes locus labels with ``allele:`` so they
cannot be mistaken for reserved metadata columns. It writes integers directly, without promoting them
to floating-point strings when another sample has a missing call.

Unplaced samples
----------------

Samples with no usable allele calls stay in the basket. Their IDs, labels, and
reasons are stored in the RQ job's ``unplaced_samples`` metadata and returned by
job polling. Only callable profiles are sent to the worker. The tree view lists
unplaced samples separately and does not assign them positions or distances.
Newick exports therefore contain the placed samples only. A single placed
sample produces a single-node tree; a selection with no placed samples is
rejected with a notice.

The worker checks that the returned tree contains every expected placed sample
exactly once. It rejects all-missing rows instead of silently dropping them,
including rows submitted by older clients.
