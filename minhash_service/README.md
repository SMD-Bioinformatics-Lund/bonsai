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
## Repairing the index

After deploying these fixes to every MinHash worker, pause similarity searches
and run these commands in the service environment
with its usual MongoDB connection and signature-volume configuration:

```sh
minhash-service recreate-index --dry-run
minhash-service recreate-index --force
minhash-service check-integrity
```

The dry run lists the eligible sample count without changing files or flags.
The rebuild validates every eligible signature, replaces the collection with one
entry per checksum, and reconciles index flags for the configured k-mer size.
It restores missing entries and removes historical duplicates and stale entries.
An empty eligible collection clears the index. Resume searches after checking the
report. A metadata update failure is reported as an error; rerunning the rebuild
reconciles partially updated flags.

Excluded samples and samples marked for deletion are omitted. The old
`--include-excluded` option has been removed so repair follows the same eligibility
rules as normal indexing. To index an excluded sample, include it in analysis
first. The command rejects k-mer sizes different from the service configuration.

RocksDB replacement retains the previous directory until the new index has been
opened successfully and restores it if replacement fails. Replacement is a
maintenance operation: reads must be paused while it runs. A shared-volume workflow
lock automatically serializes imports, QC changes, deletions, index updates, and
cleanup with the rebuild, from metadata snapshot through flag reconciliation.
All workers must use the same signature volume; direct database edits bypass this lock.
An empty SBT collection uses a Bonsai marker file because Sourmash cannot reload
an SBT archive with no leaves; adding signatures replaces it with a normal SBT.

Deletion marks metadata first, removes index entries and stages unshared files,
then deletes metadata. Failures leave marked records for retry via the same
remove task. Staged files are verified by file checksum on retry and protected
from cleanup while metadata still references their original paths. Trash defaults
to `signature_dir/trash`; an explicit `TRASH_DIR` must also be persistent and shared
by all workers.
