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

Backfill typing summaries
------------------------

The SDK's STX result model generates the display value during normal
serialization when analysis results are uploaded or replaced. The API must use
an SDK version that includes this computed field. O/H typing uses the selected
O and H labels already provided by the parser. After upgrading, populate the STX display field
for existing multi-hit results using their stored hits:

.. code-block:: bash

   bonsai-api backfill-typing-summaries --dry-run
   bonsai-api backfill-typing-summaries

This does not require the original analysis files or change the stored gene
hits, curations, or sample dates. The command can be run repeatedly. Entries
changed by a concurrent upload are skipped and reported; rerun the command to
refresh those entries. Until backfilled, existing multi-hit STX results without
the display field show a placeholder. Older single-gene STX results and O/H
typing can be displayed directly without a backfill.

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
