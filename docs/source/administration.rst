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

Sample identity and duplicate uploads
-------------------------------------

Bonsai assigns each new sample an internal UUID. Separately, a required unique
compound index prevents duplicate ``(lims_id, sequencing.sequencing_run_id)``
pairs. ``lims_id`` is the Clarity/LIMS identifier, not the sample UUID or Lab ID.
This protection applies equally to CLI and direct API uploads, including
concurrent requests. Duplicate pairs return HTTP ``409 Conflict`` with both
identifiers in the error detail.

The index includes only records with both identifiers present as non-empty
strings. Missing, null, and blank/whitespace-only identifiers are treated as
absent on input. Non-blank identifiers are preserved exactly (including case).
Samples without a run ID or without a LIMS ID may be uploaded repeatedly;
the same LIMS ID on a different run, or a different LIMS ID on the same run,
is also allowed. Sequencing platform/instrument information can be supplied
without ``sequencing_run_id``. Clients with older schemas that require this
field must update those schemas to submit or read such sequencing records.

Before deploying this constraint, run the following read-only query against
the appropriate Bonsai database to identify existing duplicate pairs:

.. code-block:: javascript

   db.sample.aggregate([
     {$match: {
       lims_id: {$type: "string", $gt: ""},
       "sequencing.sequencing_run_id": {$type: "string", $gt: ""}
     }},
     {$group: {
       _id: {lims_id: "$lims_id", run_id: "$sequencing.sequencing_run_id"},
       count: {$sum: 1},
       sample_ids: {$push: "$sample_id"}
     }},
     {$match: {count: {$gt: 1}}}
   ])

Resolve duplicate records deliberately before deployment. Also review legacy
blank/whitespace-only identifiers, which are not automatically rewritten.
Bonsai does not delete, merge, or normalize existing sample records during
startup. If the required index cannot be created, API startup fails rather
than continuing without duplicate-upload protection. Index-creation failures
for optional performance indexes still only produce warnings.

Create and manage groups of samples
-----------------------------------

Groups can be created and managed through the front end by admin users. Groups can be created and modified from the `/groups/edit` view. Groups can also be managed through the API, which allows for automation and/ or integration into sample processing pipelines.
