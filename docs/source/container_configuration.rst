Container configuration
=======================

The services that constitutes Bonsai requires probably need to be configured to function properly or to enable/ disable some features. Docker containers are configured using parameters passed at runtime (such as those above). These parameters are separated by a colon and indicate ``<external>:<internal>`` respectively. For example, ``-p 8080:80`` would expose port ``80`` from inside the container to be accessible from the host's IP on port ``8080`` outside the container.

Ports
-----

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
-----------------------


Frontend
^^^^^^^^

.. table:: Frontend environmental variables
   :widths: auto

   +-------------------+--------------------------------+-----------------+
   | Env               | Function                       | Default         |
   +===================+================================+=================+
   | API_EXTERNAL_URL  | Container-container URL to API | http://api:8000 |
   +-------------------+--------------------------------+-----------------+
   | API_EXTERNAL_URL  | From browser URL to API        | http://api:8000 |
   +-------------------+--------------------------------+-----------------+
   | TZ                | Timezone                       | Etc/UTC         |
   +-------------------+--------------------------------+-----------------+

.. autopydantic_settings:: bonsai_app.config.Settings

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

.. autopydantic_settings:: bonsai_api.config.Settings

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
---------------

Mouting directories and files from the host file system to the container is used to make assetes, such as reference genomes or configurations, available to the software. It can also be used to make data persistant accros updates to the container which is usefull for databases.

Please ensure that the mounted asset directory match the path specified in the service configuration.

.. note::

   Please ensure that the container have permission to read mounted files and directories.

API service volumes
^^^^^^^^^^^^^^^^^^^^

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


Minhash service volumes
^^^^^^^^^^^^^^^^^^^^^^^

The genome signatures sent to the minhash service container and written to disk. The directory should be mounted to the host file system for the data to be persistant. For more information see :ref:`data persistance<Data persistance>`.

.. table:: Minhash service volume mounts.
   :widths: auto

   +--------------------+----------------------------------+
   | Volume             | Function                         |
   +====================+==================================+
   | /data/signature_db | Directory for genome signatures. |
   +--------------------+----------------------------------+
