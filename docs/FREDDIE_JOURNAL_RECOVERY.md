# Private journal persistence and recovery

20 October 2026. Local acceptance for the unchanged private research model. No source ZIP,
training, test reopening, public scoring or production promotion is authorized by this drill.

## Contract fixed before implementation

- Use a fresh owner-only directory outside the repository. The existing successful journal
  and HMAC key are read-only inputs. Preserve their hashes and never replace the original.
- Back up SQLite through its online backup API, not a file copy of an active database.
  Verify schema v1, expected tables/columns, integrity and foreign keys. Bound source size
  and backup duration. Keep a separate copy of the correct HMAC key so existing links can
  be recovered. API credentials and model weights are not journal-backup contents.
- Publish a verified backup manifest only after database, key and logical table fingerprints
  reconcile. Checksums detect corruption within a trusted owner-controlled directory; they
  are not signatures or independent attestations. Failed artifacts remain private evidence.
- Restore only into a new directory. Verify manifest, checksums, schema, logical rows and key
  identity before admitting a restored journal. Reject corrupt database/key/metadata and
  refuse overwrite of an existing state directory. Backups and originals stay unchanged.
- Run the accepted image as the host non-root UID with read-only root, no capabilities/new
  privileges, two CPUs, 2GiB, bounded PIDs/tmpfs, network-none and no published port. Only
  the owner-only journal directory is writable; the model/token package stays read-only.
  Actively reject write attempts under the application root and read-only model package;
  verify that the HMAC key is absent from the API state mount. Probe inside its namespace.
  Disable automatic health probes during this bounded drill
  so only explicit requests add events. This is not a production healthcheck policy.
- Successful HTTP score IDs must exist in the committed journal. Remove and recreate the
  test-owned container against the same bind mount; all earlier rows must remain unchanged,
  and another score must persist. This verifies persistence across container replacement.
- Temporarily withdraw only the test-copy journal file while the server runs. A subsequent
  score must return503 without a probability. Preserve any fault-created empty file separately,
  return the intact journal and confirm normal writes resume. A chmod-only fault on this
  Docker Desktop bind mount did not stop writes and is retained as a failed preliminary
  drill; file mode alone is not accepted as proof of write failure or storage isolation.
- Take a verified backup while the audited API is alive. Generate a successful request after
  the backup, then recover the snapshot into a fresh directory and container. Earlier rows
  must match; the later request must be absent and explicitly accounted for as outside the
  backup recovery point. Do not claim zero data loss or zero downtime. Verify new persisted
  scoring and unchanged model probability after recovery. Record measured local timing.
- Corrupt only a separate disposable backup copy and require rejection before restore.
  Always remove only containers bearing this run's unique ownership label. Preserve state,
  backup, logs and private receipts; never prune images, unrelated containers or volumes.

## Technical basis

[Python sqlite3.Connection.backup](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.backup)
supports backups while other clients access the source. The [SQLite online backup overview](https://www.sqlite.org/backup.html)
explains consistent database snapshots. CreditLens additionally checks its application schema,
logical rows and key dependency; using the API alone does not establish recovery acceptance.

## Remaining production requirements

This is a same-host local drill with declared synthetic context/outcomes, no external ingress
or failover. It does not verify off-host disaster recovery, encrypted remote backups, scheduled
retention, multi-worker writes, token rotation, lender SLOs, authentic servicing availability,
usage rights or an operational pilot. Fintech production scoring remains HOLD.


## Implemented local verification

The accepted-model Docker drill passed container replacement with unchanged earlier rows,
HTTP503on a withdrawn test-copy journal, repaired committed writes, verified online backup,
fresh-container recovery and rejection of a corrupt backup before creating a restore target.
The request after backup was excluded from restored state and explicitly reconciled as one
successful event outside the recovery point. The HMAC key was restored separately from the
API state mount; no key was exposed to the API container. Original owner evidence and model
artifacts remain unchanged. Failed preliminary evidence is retained privately.

Local software checks:355tests passed,4skipped,8existing dependency warnings. Black/isort/Ruff,
mypy96source files and strict checks of the three operations scripts pass. Combined tested
source/backup coverage rounds to82%; the backup utility is84%. CLI/time-limit branches and
some exceptional paths are uncovered. Actual Docker orchestration is exercised separately,
not treated as comprehensive unit coverage. Neither coverage nor a same-host drill is an
operating release gate by itself.

Reusable commands are `python -m scripts.research_journal_backup backup` or `restore`, with
explicit private inputs and a fresh `--output`. The bounded real-model drill is
`python -m scripts.smoke_research_journal` with `--image`, `--bundle`, `--token-file`,
`--snapshot`, `--monitoring-receipt`, fresh `--output` and `--confirm-synthetic`.
The image's public-source hash, verification/dependency script hashes, accepted bundle,
synthetic input and source journal bind the private receipt. `--assistant-check` marks an
assistant execution; the default origin is an unverified local command identity.
