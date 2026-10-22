Administration
==============

Users and admins administer Bonsai through either the API command line interface or the Bonsai front end. Bonsai has three predefined user roles (*user*, *uploader*, and *admin*) with different levels of privileges. The uploader role has only write permissions and is intended for automation scripts that upload new samples or create groups. A user with an uploader role cannot retrieve information from the database to minimize the threat vector.

The user can view samples and groups and post comments but not upload new results or manage sample groups. The user role should be enough for most users.

The admin user role grants full permission to create, modify, and read all data through the API entry points.

Index database
--------------

The database must be indexed for Bonsai to work correctly. Indexes speed up
common queries and enforce uniqueness constraints. The API ensures indexes
exist during startup; they can also be created explicitly using the Bonsai API
command line interface. See the sample-identity section below for the required
duplicate-upload constraint. If you are running the containerized version of
Bonsai, execute the CLI commands in the container.

.. code-block::bash

   # normal command
   $ bonsai_api index

Check sample integrity
----------------------

Run ``doctor`` in the API container to check all samples for potentially missing
alignment and index data:

.. code-block:: bash

   docker compose exec api bonsai-api doctor

The command prints a report grouped by sample, with resource types, reasons,
and paths where available. If all checks complete without findings, it prints
``No issues found``. All assays require alignment files and their indexes,
SKA indexes, and MinHash signatures. The command checks every sample without
pagination and does not change sample records, files, or analysis indexes.

Alignment paths use the same rules as IGV under ``annotations_dir``, including
symlinks. Files must be present, readable, and nonempty. SKA and MinHash checks
run on their respective workers, where the files are mounted; both workers
must be running the doctor-capable version. MinHash checks inspect search-index
membership as well as metadata flags and account for intentional QC exclusions
and shared signatures.

Unavailable services, worker failures, and timeouts are reported as incomplete
checks. Exit codes are ``0`` for no issues, ``1`` for potential problems, and
``2`` for incomplete checks. Each worker batch has a 60-second timeout. The
report reflects data observed during the scan; uploads or deletions in progress
may warrant a repeat check after they finish.

Future deep validation
~~~~~~~~~~~~~~~~~~~~~~

``--deep`` is not implemented in this iteration. A future option could run
format-aware checks where each artifact is stored: alignment structural
validation followed by indexed region queries to check alignment/index
compatibility, SKA parsing and header checks, and MinHash signature parsing
and checksum comparison against stored metadata. It should use separate
execution limits, preserve the normal report structure, and distinguish
corruption from unavailable validation tools or incomplete checks. Full
alignment decoding may be needed beyond a quick structural check.

Create users
------------

Create an admin user with the CLI. There are three built in user roles (*user*, *uploader*, and *admin*).  The user role has permission to retrieve data and comment on isolates and should be the default user role.  *Uploader* has permission to create and modify data but cannot view isoaltes, this role is inteded for uploading data to the database. The *admin* has full permission to view, create, modify and delete data.

.. code-block:: bash

   docker-compose exec api bonsai_api create-user -u admin                 \
                                                  -p admin                 \
                                                  --fname Place            \
                                                  --lname Holder           \
                                                  -m place.holder@mail.com \
                                                  -r admin

Additional users can be created in the WebUI in the admin panel (``http://your-ip/admin/users``) or by using the CLI as above.

Upload samples
--------------

JASEN analysis results are uploaded to Bonsai using HTTP requests to the Bonsai API where the analysis result in JSON format and signature file is uploaded separately. Bonsai includes a simple upload bash script that can upload a sample and assign it to a group. The script is located in the scripts directory.

.. code-block:: bash

   ./scripts/upload_sample.py                                        \
      --api localhost:8011                                           \ 
      --group <optional: group_id of group to associate sample with> \
      -u <username>                                                  \
      -p <password>                                                  \
      --input /path/to/input.json

The script demonstrates basic sample management using the API routes and these could be included in your automations for sample processing.

Create and manage groups of samples
-----------------------------------

Groups can be created and managed through the front end by admin users. Groups can be created and modified from the `/groups/edit` view. Groups can also be managed through the API, which allows for automation and/ or integration into sample processing pipelines.
