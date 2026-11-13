Allele clustering service
=========================

The allele clustering service subscribes to the Redis database and listens for jobs on the `allele_clustering` queue. The exposed functions are located in `tasks.py`.

Tasks
-----

.. autofunction:: allele_cluster_service.tasks.cluster

Scheme compatibility
--------------------

MLST and cgMLST require a verifiable scheme identity and matching complete locus
sets before clustering. Unknown identity blocks the affected allele method;
matching locus names alone do not establish that allele databases match.
For cgMLST, the declared scheme and the chewBBACA database name/version are
combined when the selected analysis's own pipeline run supplies them. The latest
pipeline run is not substituted for that run. A declared scheme is used when
database provenance is unavailable. Legacy records with neither form of identity
are blocked. Empty profiles do not supply locus-set evidence.

``POST /cluster/validate`` checks both allele methods for the selected
``sampleIds``. The basket disables each incompatible method and shows its
notice while other methods remain available. Submission repeats the checks,
so stale browser state or direct requests cannot bypass them.
