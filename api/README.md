# Mimer API Server

The API service used by Mimer to store and fetch sample information.

## Setup

Use the included cli to conduct the initial setup of the database. The command will create the required indexes and create an admin user that can be used for creating additional users, groups and upload samples.

```bash
python run_mimer.py setup
```

## Upload information

Operations like uploading samples, creating groups and users are done via the REST API through `post` and `put` HTTP commands with an admin account. These commands can be easily scriptable and automated.

## Look up a sequencing record

Uploaded sample IDs are stored as `external_sample_id` and may occur in several
sequencing runs. `GET /samples/external/{external_sample_id}` returns a record
only when the match is unique. Add `?sequencing_run_id=RUN-123` to select a run.
The endpoint returns HTTP 404 when no record matches and HTTP 409 when several
still match. Use the record's internal `sample_id` for subsequent operations.
