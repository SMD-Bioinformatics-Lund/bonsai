# Mimer API Server

The API service used by Mimer to store and fetch sample information.

## Setup

Use the included cli to conduct the initial setup of the database. The command will create the required indexes and create an admin user that can be used for creating additional users, groups and upload samples.

```bash
python run_mimer.py setup
```

## Upload information

Operations like uploading samples, creating groups and users are done via the REST API through `post` and `put` HTTP commands with an admin account. These commands can be easily scriptable and automated.