Administration
==============

Users and admins administer Bonsai through either the API command line interface or the Bonsai front end. Bonsai has three predefined user roles (*user*, *uploader*, and *admin*) with different levels of privileges. The uploader role has only write permissions and is intended for automation scripts that upload new samples or create groups. A user with an uploader role cannot retrieve information from the database to minimize the threat vector.

The user can view samples and groups and post comments but not upload new results or manage sample groups. The user role should be enough for most users.

The admin user role grants full permission to create, modify, and read all data through the API entry points.

Index database
--------------

The database must be indexed for Bonsai to work correctly. The database indexes support and speed up common queries and enforces restriction on the data. For instance, will the indexes prevent duplicated sample IDs and sample group IDs? The indexes are created using the Bonsai API command line interface. Note that if you are running the containerized version of Bonsai, you must execute the commands in the container.

.. code-block::bash

   # normal command
   $ bonsai_api index

Create users
------------

Users are also created through the API. You must specify the username, password, and user role when you create the user.

.. code-block::bash

   # normal command
   $ bonsai_api create-user --u <username> -p <password> -m <email> --role <admin|user|uploader>

Upload samples
--------------

JASEN analysis results are uploaded to Bonsai using HTTP requests to the Bonsai API where the analysis result in JSON format and signature file is uploaded separately. Bonsai includes a simple upload bash script that can upload a sample and assign it to a group. The script is located in the scripts directory.

.. code-block:: bash

   ./scripts/upload_sample.sh                                        \
      --api localhost:8011                                           \ 
      --group <optional: group_id of group to associate sample with> \
      -u <username>                                                  \
      -p <password>                                                  \
      --input /path/to/input.json

The script demonstrates basic sample management using the API routes and these could be included in your automations for sample processing.

Create and manage groups of samples
-----------------------------------

Groups can be created and managed through the front end by admin users. Groups can be created and modified from the `/groups/edit` view. Groups can also be managed through the API, which allows for automation and/ or integration into sample processing pipelines.
