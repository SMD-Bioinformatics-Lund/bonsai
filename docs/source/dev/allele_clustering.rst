Allele clustering service
=========================

The allele clustering service subscribes to the Redis database and listens for jobs on the `allele_clustering` queue. The exposed functions are located in `tasks.py`.

Tasks
-----

.. autofunction:: allele_cluster_service.tasks.cluster

Pairwise comparability
----------------------

Before submitting an MLST/cgMLST job, every pair of usable profiles must share
at least one positive allele call. Missing calls do not establish comparability.
A chain of overlapping profiles is insufficient if any pair has no shared called
locus. Such selections receive a validation error, since zero jointly called loci
is not evidence of zero genetic distance. The rule does not impose a minimum
coverage threshold beyond one jointly called locus or change distance scaling.
