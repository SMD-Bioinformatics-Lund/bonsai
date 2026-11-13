Allele clustering service
=========================

The allele clustering service subscribes to the Redis database and listens for jobs on the `allele_clustering` queue. The exposed functions are located in `tasks.py`.

Tasks
-----

.. autofunction:: allele_cluster_service.tasks.cluster

Sample accounting
-----------------

Samples without usable allele calls remain in the basket and are listed as
unplaced beside the tree. Only usable samples are passed to the worker and
included in Newick or tree metadata. Unplaced samples have no assigned position
or genetic distance. One usable sample produces a single-node tree; a selection
with none is rejected. The queue retains unplaced sample IDs, labels, and reasons
in job metadata, exposed as ``unplaced_samples`` by job-status polling. The
worker verifies expected sample IDs before and after clustering.
