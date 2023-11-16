# Minhash service

Service operating on Minhashes for the Bonsai API.

## Configuration

The minhash service is configured by either modifying the `config.py` file or by setting the corresponding environmental variables. The following variables are mandatory and need to be set to match your system

- `KMER_SIZE` - Must match the size used when generating the signatures
- `DB_PATH` - Path to the folder where genome signatures and index are stored
- `REDIS_HOST` - Redis server host URL
- `REDIS_PORT` - Redis server port

## Tasks

### add_signature

Write signature to database

### remove_signature

Remove signature from database

### index

Add signature to database index

### similar

Find signatures similar to reference

### cluster

Cluster signatures with their minhash profile

### find_similar_and_cluster

Combination of `similar` and `cluster`. For first finding signatures similar to reference and then cluster in one job.