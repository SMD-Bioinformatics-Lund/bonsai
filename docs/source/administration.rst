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

Run ``doctor check`` in the API container to inspect registered samples without
changing sample records, files, or analysis indexes:

.. code-block:: bash

   docker compose exec api bonsai-api doctor check
   docker compose exec api bonsai-api doctor check --assay my-assay
   docker compose exec api bonsai-api doctor check --sample LAB_ID --sample SAMPLE_UUID
   docker compose exec api bonsai-api doctor check --file-type alignment
   docker compose exec api bonsai-api doctor check --group-by file-type
   docker compose exec -T api bonsai-api doctor check --format json > doctor-report.json

The API checks alignments and their indexes under ``annotations_dir`` using the
same path rules as IGV, including symlinks. Every registered alignment must have
a nonempty, readable file and index. SKA and MinHash checks run as batches on
their respective workers, where the files are mounted. Both workers must be
running the doctor-capable version. Missing resource references are reported
even when there is no file path to check. The command scans all matching
records, without the API's normal sample-list pagination.

``--assay`` matches the current pipeline run selected by
``last_pipeline_run_id``, as in the sample summary; historical assays do not
match. Assay names are exact and case-sensitive. ``--sample`` accepts internal
sample IDs, external Lab IDs, or LIMS IDs, and may match multiple records when
an external ID is shared. Repeat either option to select several values.
Different filters intersect. Explicit sample IDs that do not match the final
selection, or an assay selection with no matches, make the report incomplete.

``--file-type`` accepts ``alignment`` (including its index), ``ska``, and
``minhash`` (including search-index membership), and is repeatable. Findings
are grouped by sample by default; ``--group-by file-type`` groups alignment
indexes and MinHash search-index findings separately. Reports include sample
IDs, Lab/LIMS IDs, assay names, reasons, paths where available, and counts of
checked and affected samples. ``--format json`` produces a single JSON object
with ``status``, ``selection``, ``checked_samples``, ``affected_samples``,
``group_by``, ``groups``, and ``errors``. ``--output PATH`` writes either report
format to a file inside the container.

MinHash checks use the worker's configured k-mer size, inspect the actual
search index as well as metadata flags, and retain the requirement for a
signature file when QC has failed. A failed sample intentionally excluded
from search is valid; a shared checksum may remain indexed for other eligible
samples.

By default, all assays require alignment, SKA, and MinHash resources. Override
this only for assays that intentionally produce fewer resource categories,
using the API's configuration file:

.. code-block:: toml

   [doctor_assay_requirements]
   amplicon = ["alignment"]
   assembly = ["ska", "minhash"]

The equivalent environment variable is
``DOCTOR_ASSAY_REQUIREMENTS='{"amplicon":["alignment"]}'``. Unlisted assays
and records without a current assay use all three requirements. A file-type
filter narrows the required categories; it does not override assay exemptions.

Exit codes are ``0`` for a completed check with no findings, ``1`` for detected
problems, and ``2`` for incomplete checks, even if some problems were also
found. An empty database reports zero checked samples explicitly. Worker
failures, unavailable services, and timeouts are reported as incomplete,
not as missing files or a clean result. ``--timeout SECONDS`` controls the
wait and execution limit per worker batch (default: 60). Pending jobs expire
after the same interval. Increase the timeout for large datasets or busy
queues. No repairs or email notifications are performed. Reports reflect the
data observed during the scan; uploads or deletions in progress may warrant
a repeat check after they finish.

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
