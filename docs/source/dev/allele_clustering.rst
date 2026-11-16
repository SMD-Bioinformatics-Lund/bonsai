Allele clustering service
=========================

The allele clustering service subscribes to the Redis database and listens for jobs on the `allele_clustering` queue. The exposed functions are located in `tasks.py`.

Tasks
-----

.. autofunction:: allele_cluster_service.tasks.cluster

Scheme compatibility
--------------------

MLST requires the same detected typing scheme, even within one analysis profile:
broad profiles can auto-detect different MLST schemes. Matching MLST schemes may
be compared across analysis profiles.

cgMLST requires the same analysis profile, stored as ``assay`` on the pipeline run
that produced the selected cgMLST result. Each profile is currently assumed to
define one compatible cgMLST scheme; supporting multiple schemes per profile
will require explicit scheme identity. Neither a declared cgMLST scheme nor
database or software versions replace this profile check. The latest pipeline
run is not substituted for the producing run.

Both methods also require matching complete locus sets. Unknown MLST scheme or
cgMLST profile identity blocks the affected method; matching locus names alone
do not establish compatibility. Missing allele calls retain their locus keys.
Empty profiles do not supply locus-set evidence. These identity restrictions do
not apply to MinHash.

``POST /cluster/validate`` checks both allele methods for the selected
``sampleIds``. The basket disables each incompatible method and shows its
notice while other methods remain available. Submission repeats the checks,
so stale browser state or direct requests cannot bypass them.
