Installation
============

.. _installation:

Bonsai consist of multiple services such as a frontend, an API, and tools for various clustering methods that needs to be configured during installation. It’s therefore recommended to install Bonsai and its services using the pre-built docker containers stored on Docker Hub. This requires that you have installed `docker <http://www.docker.com>`_ and preferably `docker-compose`. The prebuilt images currently support the x86-64 architecture.

Installing Bonsai using docker-compose and setup involves the following steps.

#. :ref:`Create a docker-compose file<Setup Bonsai with docker-compose>`.
#. :ref:`Setup IGV (optional)<Setup IGV integration>`.
#. :doc:`Configure LDAP based authentication (optional)</dev/login_systems>`.
#. Start the Bonsai with ``docker-compose up -d``
#. :ref:`Create indexes for the database<Create database indexes>`.
#. :ref:`Create an admin user<Create an admin user>`.
#. :ref:`Upload samples<Upload samples to Bonsai>`.

Please note that your ``docker-compose.yml`` file might be different from the minimal example in the documentaiton depending on your network and server environment. You can configure the different services using environmental variables (defined in the docker-compose file). See advanced :ref:`container configuration<Container configuration>` for the available options. In rare instances you might need to  or by editing the related config files (`frontend config <https://github.com/Clinical-Genomics-Lund/bonsai/blob/master/frontend/app/config.py>`_ and `api config <https://github.com/Clinical-Genomics-Lund/bonsai/blob/master/api/app/config.py>`_) and mount these to the container using `volume mounts <https://docs.docker.com/storage/volumes/>`_.

Some containers requires access to directories or files the host file system in order for all features to function or for data to be persistant accros updates to container images. These can be made available using using `docker volumes <https://docs.docker.com/storage/volumes/>`_. For more information see the sections on :ref:`data persistance<Data persistance>`, :ref:`setup IGV<Setup IGV integration>`, and the documentaiton of volume mounts in the :ref:`advanced container configuration<Container configuration>`.

Setup Bonsai with docker-compose
--------------------------------

Use docker-compose to get started creating the Bonsai containers and configure their access to a mongo database. Some containers must be configured using a combination of environmental variables and volume mounts to either function properly or for data to be :ref:`persistant<Data persistance>`. See :ref:`container configuration<Container configuration>` for more information on how to configure docker containers.

.. code-block:: yaml

   services: 
      mongodb:
         image: mongo:latest
         networks:
            - bonsai-net

      redis:
         image: redis:7.0.10
         networks:
            - bonsai-net

      frontend:
         image: clinicalgenomicslund/bonsai-app:0.7.0 
         depends_on:
            - mongodb
            - api
         ports: 
            - "8000:8000"
         networks:
            - bonsai-net

      api:
         image: clinicalgenomicslund/bonsai-api:0.7.0 
         depends_on:
            - mongodb
            - minhash_service
            - allele_cluster_service
         ports: 
            - "8001:8000"
         networks:
            - bonsai-net

      minhash_service:
         image: clinicalgenomicslund/bonsai-minhash-clustering:0.2.0 
         depends_on:
            - redis
         volumes:
            - "./volumes/api/genome_signatures:/data/signature_db"
         networks:
            - bonsai-net

      allele_cluster_service:
         image: clinicalgenomicslund/bonsai-allele-clustering:0.2.0
         depends_on:
            - redis
         networks:
            - bonsai-net

   networks:
      bonsai-net:
         driver: bridge

Start the services with ``docker-compose up -d`` 

Version Tags
~~~~~~~~~~~~

This project provides various versions on Docker Hub that are available via tags. Please read the description carefully and exercise caution when using unstable or development tags.

.. table::
   :widths: auto

   +------------+----------------------------------------+
   | Tag        | Description                            |
   +============+========================================+
   | latest     | Commits to the master branch of Bonsai |
   +------------+----------------------------------------+
   | <version>  | Releases of Bonsai                     |
   +------------+----------------------------------------+

Create database indexes
-----------------------

The database must be indexed for Bonsai to work correctly. The database indexes support and speed up common queries and enforces restriction on the data. For instance, will the indexes prevent duplicated sample IDs and sample group IDs? The indexes are created using the Bonsai API command line interface. Note that if you are running the containerized version of Bonsai, you must execute the commands in the container.

.. code-block:: bash

   docker-compose exec api bonsai_api index

Create an admin user
--------------------

Create an admin user with the CLI. The *admin* has full permission to view, create, modify and delete data and can be used to login, upload samples, and create additional users.

.. code-block:: bash

   docker-compose exec api bonsai_api create-user -u admin                 \
                                                  -p admin                 \
                                                  --fname Place            \
                                                  --lname Holder           \
                                                  -m place.holder@mail.com \
                                                  -r admin

Additional users can be created in the WebUI in the admin panel (``http://your-ip/admin/users``) or by using the CLI as above. For more information see :ref:`create users<Create users>`.

Setup IGV integration
---------------------

Bonsai uses IGV to visualise the read depth for called SNVs and structural variants (SV). This can help interpreting if a called variant is a true or false positive. IGV uses the reference genome sequences with annotated genes, the mapped reads in ``bam`` or ``cram`` format and optionally called variants and regions of interests. These files are either used as assets by Jasen or genreated for the sample and published in the pipeline output directory.

These files are served by the API and therefore needs to be accessable by the container at the paths specified by the environmental variables ``REFERENCE_GENOMES_DIR``, ``ANNOTATIONS_DIR`` and the path where Jasen publishes its results. 

.. note::

   IGV needs access to fasta indexes and bam indexes in order to function well.

Reference genomes
~~~~~~~~~~~~~~~~~

These should be the same as the reference gneomes used by Jasen. You can use the `Makefile <https://github.com/genomic-medicine-sweden/jasen/blob/master/Makefile>`_ from Jasen to download the genomes, their indexes, and the tbprofiler database. Alternatively you could copy existing files from your Jasen installation to the directories you mount to the API container.

Reference genomes and the corresponding GFF file should be copied to the directory you mount to the path in ``REFERENCE_GENOMES_DIR``. The BED files describing regions of interests should be copied to the directory you mount to the ``ANNOTATIONS_DIR`` path.

BAM and VCF files
~~~~~~~~~~~~~~~~~

The Bonsai API needs access to directory where Jasen publishes its result because the BAM and VCFs are not uploaded to the API. The result directory could me mounted using docker volumes if its accessable by the host machine. The expected path can be found in the analysis result json file under the field name ``read_mapping`` and ``genome_annotation``.

Accessing the web interface
---------------------------

To access the web interface, access the URL ``http://localhost:8000`` in your web browser.

If this doesn't work, you might want to run ``docker container ls`` and make sure that a frontend container is running. Secondly ensure that there are not errors in the ``frontend`` and ``api`` container logs.

Upload samples to Bonsai
------------------------

Use the `upload_sample.py <https://github.com/Clinical-Genomics-Lund/bonsai/blob/master/scripts/upload_sample.py>`_ script to add analysis result and genome signature file to the database.


.. code-block:: bash

   ./scripts/upload_sample.py                                        \
      --api localhost:8011                                           \ 
      --group <optional: group_id of group to associate sample with> \
      -u <username>                                                  \
      -p <password>                                                  \
      --input /path/to/input.json


Data persistance
----------------

The data is not persitant between docker container updates by default as all data is kept in the container. You have to mount the mongo database and the API genome signature database to the host OS to make the data persitant. The volume mounts can be configured in the ``docker-compose.yaml`` file. If you mount the databases to the host OS you have to ensure that they have correct permissions so the container have read and write access to these files.

Use the following command to get the user and group id of the user in the container.

.. code-block:: bash

   $ docker-compose run --rm mongodb id
   # uid=1000(worker) gid=1000(worker) groups=1000(worker)

Use ``chown -R /path/to/volume_dir 1000:1000`` to change the permission of the folders you
mount to the container.

The following are an example volume mount configuration. See the `docker-compose <https://docs.docker.com/storage/volumes/>`_
documentation for more information on volume mounts.

.. code-block:: yaml

   services: 
      mongodb:
         volumes:
            - "./volumes/mongodb:/data/db"

      api:
         volumes:
            - "./volumes/api/genome_signatures:/data/signature_db"
