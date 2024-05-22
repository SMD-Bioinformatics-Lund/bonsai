Installation
============

.. _installation:

Bonsai consist of multiple services such as a frontend, an API, and tools for various clustering methods that needs to be configured during installation. It’s therefore recommended to install Bonsai and its services using the pre-built docker containers stored on Docker Hub. This requires that you have installed `docker <http://www.docker.com>`_ and preferably `docker-compose`. The prebuilt images currently support the x86-64 architecture.

Please note that your ``docker-compose.yml`` file might be different from the minimal example in the documentaiton depending on your network environment. In addition are most configuration options definable using environmental variables but in some instances you might need to edit `frontend config <https://github.com/Clinical-Genomics-Lund/bonsai/blob/master/frontend/app/config.py>` and `api config <https://github.com/Clinical-Genomics-Lund/bonsai/blob/master/api/app/config.py>` files depending on your network environment.

Version Tags
------------

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

Application setup
-----------------

The web UI can be found at ``http://your-ip:8000``.

Use docker-compose to get started creating the Bonsai containers and configure their access to a mongo database.

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
      image: clinicalgenomicslund/bonsai-app:0.6.0 
      depends_on:
         - mongodb
         - api
      ports: 
         - "8000:8000"
      networks:
         - bonsai-net

   api:
      image: clinicalgenomicslund/bonsai-api:0.6.0 
      depends_on:
         - mongodb
         - minhash_service
         - allele_cluster_service
      ports: 
         - "8001:8000"
      networks:
         - bonsai-net

   minhash_service:
      image: clinicalgenomicslund/bonsai-minhash-clustering:0.1.2 
      depends_on:
         - redis
      volumes:
         - "./volumes/api/genome_signatures:/data/signature_db"
      networks:
         - bonsai-net
      command: "minhash_service"

   allele_cluster_service:
      image: clinicalgenomicslund/bonsai-allele-clustering:0.1.0
      depends_on:
         - redis
      networks:
         - bonsai-net
      command: "cluster_service"

   networks:
   bonsai-net:
      driver: bridge

Start the services with ``docker-compose up -d`` 

Use the Bonsai api command line interface to create the required database indexes.

.. code-block:: bash

   docker-compose exec api bonsai_api index

Create an admin user with the CLI. There are three built in user roles (*user*, *uploader*, and *admin*).  The user role has permission to retrieve data and comment on isolates and should be the default user role.  *Uploader* has permission to create and modify data but cannot view isoaltes, this role is inteded for uploading data to the database. The *admin* has full permission to view, create, modify and delete data.

.. code-block:: bash

   docker-compose exec api bonsai_api create-user -u admin                 \
                                                  -p admin                 \
                                                  --fname Place            \
                                                  --lname Holder           \
                                                  -m place.holder@mail.com \
                                                  -r admin


Container parameters
--------------------

Containers are configured using parameters passed at runtime (such as those above). These parameters are separated by a colon and indicate `<external>:<internal>` respectively. For example, `-p 8080:80` would expose port `80`` from inside the container to be accessible from the host's IP on port `8080` outside the container.

Ports
~~~~~

.. table::
   :widths: auto

   +-----------------+----------+
   | Parameter       | Function |
   +=================+==========+
   | 8000            | WebUI    |
   +-----------------+----------+
   | 8001            | API      |
   +-----------------+----------+
   | 27017           | Mongo db |
   +-----------------+----------+
   | 6380            | Redis    |
   +-----------------+----------+

Environmental variables
~~~~~~~~~~~~~~~~~~~~~~~

The services that constitutes Bonsai can be configured with environmental variables. The configuration available differs depending on the service.

Frontend
^^^^^^^^

.. table:: Frontend environmental variables
   :widths: auto

   +-----------------+--------------------+-----------------+
   | Env             | Function           | Default         |
   +=================+====================+=================+
   | BONSAI_API_URL  | URL to API service | http://api:8000 |
   +-----------------+--------------------+-----------------+

API service
^^^^^^^^^^^

Here are the general configuration options for the API service. See the :doc:`documentation on login systems </dev/login_systems>` for information on how to configure LDAP based authentication.

.. table:: API environmental variables
   :widths: auto

   +-----------------------------+-----------------------------------------------------+------------------------+
   | Env                         | Function                                            | Default                |
   +=============================+=====================================================+========================+
   | ALLOWED_ORIGINS             | Configure allowed origins as commma separated list. |                        |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | DATABASE_NAME               | Database name                                       | bonsai                 |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | DB_HOST                     | Hostname of mongodb                                 | mongodb                |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | DB_PORT                     | Mongodb port                                        | 27017                  |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | REDIS_HOST                  | Hostname of redis server                            | redis                  |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | REDIS_PORT                  | Port of redis server                                | 6379                   |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | REFERENCE_GENOMES_DIR       | Path to directory with reference genomes            | /tmp/reference_genomes |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | ANNOTATIONS_DIR             | Path to directory where genome annotation is stored | /tmp/annotations       |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | SECRET_KEY                  | Authentication token secret key                     |                        |
   +-----------------------------+-----------------------------------------------------+------------------------+
   | ACCESS_TOKEN_EXPIRE_MINUTES | Authentication token expiration time.               | 180                    |
   +-----------------------------+-----------------------------------------------------+------------------------+

Minhash service
^^^^^^^^^^^^^^^

.. table:: Minhash service environmental variables
   :widths: auto

   +----------------------+----------------------------------------------+------------------------+
   | Env                  | Function                                     | Default                |
   +======================+==============================================+========================+
   | SIGNATURE_KMER_SIZE  | Kmer size used to build signature files.     | 31                     |
   +----------------------+----------------------------------------------+------------------------+
   | GENOME_SIGNATURE_DIR | Path to directory where signatures are kept. | /data/signature_db     |
   +----------------------+----------------------------------------------+------------------------+
   | REDIS_HOST           | Redis server hostname                        | redis                  |
   +----------------------+----------------------------------------------+------------------------+
   | REDIS_PORT           | Redis server port                            | 6379                   |
   +----------------------+----------------------------------------------+------------------------+

Allele clustering service
^^^^^^^^^^^^^^^^^^^^^^^^^

.. table:: Allele cluster service environmental variables
   :widths: auto

   +----------------------+----------------------------------------------+------------------------+
   | Env                  | Function                                     | Default                |
   +======================+==============================================+========================+
   | REDIS_HOST           | Redis server hostname                        | redis                  |
   +----------------------+----------------------------------------------+------------------------+
   | REDIS_PORT           | Redis server port                            | 6379                   |
   +----------------------+----------------------------------------------+------------------------+

Volume mappings
~~~~~~~~~~~~~~~

Mouting directories and files from the host file system to the container is used to make assetes, such as reference genomes or configurations, available to the software. It can also be used to make data persistant accros updates to the container which is usefull for databases.

Please ensure that the mounted asset directory match the path specified in the service configuration.

.. note::

   Please ensure that the container have permission to read mounted files and directories.

API service
^^^^^^^^^^^

The API can serve reference genome sequences and annotation files to the integrated IGV browser. These could be stored on the host file system and mounted to the docker container.

.. table:: API service volume mounts.
   :widths: auto

   +------------------------+----------------------------+
   | Volume                 | Function                   |
   +========================+============================+
   | /tmp/reference_genomes | Reference genomes for IGV. |
   +------------------------+----------------------------+
   | /tmp/annotations       | IGV annotation files.      |
   +------------------------+----------------------------+


Minhash service
^^^^^^^^^^^^^^^

The genome signatures sent to the minhash service container and written to disk. The directory should be mounted to the host file system for the data to be persistant. For more information see `Data persistance`_.

.. table:: API service volume mounts.
   :widths: auto

   +--------------------+----------------------------------+
   | Volume             | Function                         |
   +====================+==================================+
   | /data/signature_db | Directory for genome signatures. |
   +--------------------+----------------------------------+

Setup IGV integration
---------------------

Bonsai uses IGV to visualise the read depth for called SNVs and structural variants (SV). This can help interpreting if a called variant is a true or false positive. IGV uses the reference genome sequences with annotated genes, the mapped reads in ``bam`` or ``cram`` format and optionally called variants and regions of interests. These files are either used as assets by Jasen or genreated for the sample and published in the pipeline output directory.

These files are served by the API and therefore needs to be accessable by the container at the paths specified by the environmental variables ``REFERENCE_GENOMES_DIR``, ``ANNOTATIONS_DIR`` and the path where Jasen publishes its results. 

.. note::

   IGV needs access to fasta indexes and bam indexes in order to function well.

Reference genomes
~~~~~~~~~~~~~~~~~

These should be the same as the reference gneomes used by Jasen. Either use the `Makefile <https://github.com/genomic-medicine-sweden/jasen/blob/master/Makefile>` from Jasen to download these reference genomes and the tbprofiler database or copy existing files from your Jasen installation.

Reference genomes and the corresponding GFF file should be copied to the ``REFERENCE_GENOMES_DIR`` and BED files describing regions of interests should be copied to ``ANNOTATIONS_DIR``.

BAM and VCF files
~~~~~~~~~~~~~~~~~

The Bonsai API needs access to directory where Jasen publishes its result because the BAM and VCFs are not uploaded to the API. The result directory could me mounted using docker volumes if its accessable by the host machine. The expected path can be found in the analysis result json file under the field name ``read_mapping`` and ``genome_annotation``.

Accessing the web interface
---------------------------

To access the web interface, access the URL ``http://localhost:8000`` in your web browser.

If this doesn't work, you might want to run ``docker container ls`` and make sure that a frontend container is running. Secondly ensure that there are not errors in the ``frontend`` and ``api`` container logs.

Upload samples
--------------

Use the `upload_sample.py <https://github.com/Clinical-Genomics-Lund/bonsai/blob/master/scripts/upload_sample.py>` script to add analysis result and genome signature file to the database.


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
