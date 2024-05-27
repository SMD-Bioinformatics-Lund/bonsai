MinHash clustering
==================

The MinHash clustering service subscribes to the Redis database and listens for jobs on the `minhash` queue.

Tasks
-----

.. autofunction:: minhash_service.tasks.add_signature

.. autofunction:: minhash_service.tasks.remove_signature

.. autofunction:: minhash_service.tasks.add_to_index

.. autofunction:: minhash_service.tasks.remove_from_index

.. autofunction:: minhash_service.tasks.similar

.. autofunction:: minhash_service.tasks.cluster

.. autofunction:: minhash_service.tasks.find_similar_and_cluster