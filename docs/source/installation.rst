Installation
============

.. _installation:

Bonsai consist of multiple services such as a frontend, an API, and tools for various clustering methods that needs to be configured during installation. It’s therefore recommended to install Bonsai and its services using the pre-built docker containers stored on Docker Hub. This requires that you have installed `docker <http://www.docker.com>`_ and preferably `docker-compose`. The prebuilt images currently support the x86-64 architecture.

Please note that you might need to edit the :doc:`docker-compose <../docker-compose.yml>` file, :doc:`api config <./api/app/config.py>`, and :doc:`web client config <./frontend/app/config.py>` files depending on your network environment.

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

   +-----------------+--------------------+
   | Env             | Function           |
   +=================+====================+
   | BONSAI_API_URL  | URL to API service |
   +-----------------+--------------------+

API service
^^^^^^^^^^^

Here are the general configuration options for the API service. See the :doc:`documentation on login systems </dev/login_systems>` for information on how to configure LDAP based authentication.

.. table:: API environmental variables
   :widths: auto

   +-----------------------------+-----------------------------------------------------+
   | Env                         | Function                                            |
   +=============================+=====================================================+
   | ALLOWED_ORIGINS             | Configure allowed origins as commma separated list. |
   +-----------------------------+-----------------------------------------------------+
   | DATABASE_NAME               | Database name                                       |
   +-----------------------------+-----------------------------------------------------+
   | DB_HOST                     | Hostname of mongodb                                 |
   +-----------------------------+-----------------------------------------------------+
   | DB_PORT                     | Mongodb port                                        |
   +-----------------------------+-----------------------------------------------------+
   | REDIS_HOST                  | Hostname of redis server                            |
   +-----------------------------+-----------------------------------------------------+
   | REDIS_PORT                  | Port of redis server                                |
   +-----------------------------+-----------------------------------------------------+
   | REFERENCE_GENOMES_DIR       | Path to directory with reference genomes            |
   +-----------------------------+-----------------------------------------------------+
   | ANNOTATIONS_DIR             | Path to directory where genome annotation is stored |
   +-----------------------------+-----------------------------------------------------+
   | SECRET_KEY                  | Authentication token secret key                     |
   +-----------------------------+-----------------------------------------------------+
   | ACCESS_TOKEN_EXPIRE_MINUTES | Authentication token expiration time.               |
   +-----------------------------+-----------------------------------------------------+

Minhash service
^^^^^^^^^^^^^^^

.. table:: Minhash service environmental variables
   :widths: auto

   +----------------------+----------------------------------------------+
   | Env                  | Function                                     |
   +======================+==============================================+
   | SIGNATURE_KMER_SIZE  | Kmer size used to build signature files.     |
   +----------------------+----------------------------------------------+
   | GENOME_SIGNATURE_DIR | Path to directory where signatures are kept. |
   +----------------------+----------------------------------------------+
   | REDIS_HOST           | Redis server hostname                        |
   +----------------------+----------------------------------------------+
   | REDIS_PORT           | Redis server port                            |
   +----------------------+----------------------------------------------+

Allele clustering service
^^^^^^^^^^^^^^^^^^^^^^^^^

.. table:: Allele cluster service environmental variables
   :widths: auto

   +----------------------+----------------------------------------------+
   | Env                  | Function                                     |
   +======================+==============================================+
   | REDIS_HOST           | Redis server hostname                        |
   +----------------------+----------------------------------------------+
   | REDIS_PORT           | Redis server port                            |
   +----------------------+----------------------------------------------+

Volume mappings
~~~~~~~~~~~~~~~

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

Upload samples
--------------

Use the :doc:`upload_sample.py <../scripts/upload_sample.sh>` script to add analysis result and genome signature file to the database.

.. code-block:: bash

   ./scripts/upload_sample.py                                        \
      --api localhost:8011                                           \ 
      --group <optional: group_id of group to associate sample with> \
      -u <username>                                                  \
      -p <password>                                                  \
      --input /path/to/input.json

Accessing the web interface
---------------------------

To access the web interface, access the URL ``http://localhost:8000`` in your web browser.

(If this doesn't work, you might want to run ``docker container ls`` and make sure that a container based on the image ``bonsai_frontend`` is available in the list).

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
