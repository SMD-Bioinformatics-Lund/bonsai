# Bonsai

Analyze outbreak, antimicrobial resistance and virulence factors in bacteria.

Intended to visualize results from [JASEN](https://github.com/genomic-medicine-sweden/JASEN) pipeline.

## Installation

You can use `docker-compose.yml` file to quickly install Bonsai for demo and development purposes. This requires that you have [docker](www.docker.com) and *docker-compose* installed. Depending on your environment you might need to edit the [docker-compose](./docker-compose.yml) file, [api config](./server/app/config.py), and [web client config](./client/app/config.py) files.

To install Bonsai, first clone the repository and start the softwares.

```sh
# clone Bonsai
git clone git@github.com:Clinical-Genomics-Lund/cgviz.git
# navigate to project directory
cd cgviz
# start the bonsai software stack
docker-compose up -d
```

Use the Bonsai api command line interface to create the required database indexes.

```sh
docker-compose exec api bonsai_api index
```

Create an admin user with the CLI. There are three built in user roles (*user*, *uploader*, and *admin*). The user role has permission to retrieve data and comment on isolates and should be the default user role. *Uploader* has permission to create and modify data but cannot view isoaltes, this role is inteded for uploading data to the database. The *admin* has full permission to view, create, modify and delete data.

```sh
docker-compose exec api bonsai_api create-user -u admin -p admin -r admin
```
Use the `./scripts/upload_sample.sh` script to add analysis result and genome signature file to the database.

```sh
./scripts/upload_sample.sh --api localhost:8011 --group <optional: group_id of group to associate sample with> -u <username> -p <password> --input /path/to/input.json
```
