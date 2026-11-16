Allele clustering service
=========================

The allele clustering service subscribes to the Redis database and listens for jobs on the `allele_clustering` queue. The exposed functions are located in `tasks.py`.

Tasks
-----

.. autofunction:: allele_cluster_service.tasks.cluster

Basket notices
--------------

Typing compatibility notices are collapsed under a notice count in the sample
basket. Expand the count to see missing typing data, missing scheme or producing
profile identity, unreadable allele results, or incompatible schemes, profiles,
and locus sets. Details identify affected samples by Lab ID when available.
Unavailable typing results are reported separately from missing scheme metadata.

The failed-QC removal button includes the number of affected samples without a
separate warning paragraph. Sample cards retain their failed-QC highlighting.
