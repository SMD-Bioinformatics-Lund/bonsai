Configuring Bonsai
==================

Bonsai is primarily configured through environment variables. The configuration can be set in a ``.env`` file in the same directory as the ``docker-compose.yml`` file or passed directly to the Docker container. See the `docker compose reference <https://docs.docker.com/reference/compose-file/>`_ for information on how to set environment varialbes.

Some services have additional configuration files if environment variables are not enough. These are described in the relevant sections below.

In addition to environment varialbles some services have directories that should be mounted to the host file system to make data persistant accros container updates. See :ref:`Volume mappings<Volume mappings>` for more information.

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

   +-------------------+--------------------------------+-----------------------+
   | Env               | Function                       | Default               |
   +===================+================================+=======================+
   | API_INTERNAL_URL  | Container-container URL to API | http://api:8000       |
   +-------------------+--------------------------------+-----------------------+
   | API_EXTERNAL_URL  | From browser URL to API        | http://localhost:8001 |
   +-------------------+--------------------------------+-----------------------+
   | TZ                | Timezone                       | Etc/UTC               |
   +-------------------+--------------------------------+-----------------------+

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


Specific configuration files
----------------------------

API service
^^^^^^^^^^^

The API service automatically tags uploaded samples to highlight important features, such as antibiotic resistance genes or virulence genes. Some tags uses a set of thresholds defined in a toml file. The default configuration file is located in the container at ``/app/bonsai_api/thresholds.toml``. To customize the thresholds, you can create your own `thresholds.toml` file and mount it to the container.