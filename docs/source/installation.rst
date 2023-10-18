Installation
============

.. _installation:

You can use ``docker-compose.yml`` file to quickly install Bonsai for demo and development purposes.  This requires that you have `docker <http://www.docker.com>`_ and `docker-compose` installed. Depending on your environment you might need to edit the :doc:`docker-compose <../docker-compose.yml>` file, :doc:`api config <./server/app/config.py>`, and :doc:`web client config <./client/app/config.py>` files.

To install Bonsai, first clone the repository and start the softwares.

.. code-block:: bash

   # clone Bonsai
   git clone git@github.com:Clinical-Genomics-Lund/cgviz.git
   # navigate to project directory
   cd cgviz
   # start the bonsai software stack
   docker-compose up -d

Use the Bonsai api command line interface to create the required database indexes.

.. code-block:: bash

   docker-compose exec api bonsai_api index

Create an admin user with the CLI. There are three built in user roles (*user*, *uploader*, and *admin*).  The user role has permission to retrieve data and comment on isolates and should be the default user role.  *Uploader* has permission to create and modify data but cannot view isoaltes, this role is inteded for uploading data to the database. The *admin* has full permission to view, create, modify and delete data.

.. code-block:: bash

   docker-compose exec api bonsai_api create-user -u admin -p admin -r admin

Use the :doc:`upload_sample.py <../scripts/upload_sample.sh>` script to add analysis result and genome signature file to the database.

.. code-block:: bash

   ./scripts/upload_sample.sh                                        \
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