# Private inference audit and delayed-label monitoring

20 October 2026. Bounded local research integration; the accepted v4 model, calibration,
features, alert policy and consumed independent sources are unchanged. No source archive,
training, production promotion or public data/model distribution is part of this work.

## Contract fixed before implementation

- The server generates a UUID request ID, ignoring caller-supplied IDs. Return it in a
  response header and successful score body. Optional owner-only SQLite auditing outside
  Git records actual request time, route class, status, latency, model identity/checksum
  and successful probability. Never persist bearer credentials, raw features, loan IDs,
  raw URLs, IP addresses or request bodies. Auth remains before body parsing.
- When audit is enabled, a successful response requires a committed audit event. Audit
  storage failure returns 503 rather than an unaudited success. Bound local storage to
  100,000 events/64MiB and use SQLite transactions. This is local operator evidence, not
  tamper-proof centralized logging, identity attestation or a retention service.
- The trusted local monthly client may link a successful audited score with supplied
  reporting/prediction time and an HMAC loan reference, using a separate owner-only key.
  Raw loan IDs and the HMAC key are not stored in the journal or sent to the scoring API.
- Canonical quality grain is the first linked request per model checksum/key/loan/month.
  Exact retries do not multiply quality observations; changed predictions for that grain
  are rejected for review. Traffic still counts every server request. No threshold search
  or model selection uses monitoring output.
- Initial outcome intake is explicitly synthetic only. Reuse the fixed three-month
  current-to90+orREO label function. Accept only the exact next reporting months, explicit
  availability times, and a report cutoff. Future-unavailable records are excluded; gaps,
  unknown status or termination preserve censoring. Missing labels are never zero.
- Resolved labels must become available after actual scoring and by the report cutoff.
  Conflicting resolved evidence is rejected; censored updates retain prior revisions.
  Replaying identical evidence is idempotent. No corrected historical source is assigned
  invented operational availability timestamps.
- Reports separate all traffic, successful scores, canonical linked observations, pending,
  censored and resolved labels per model. Mean prediction, observed adverse rate and Brier
  are diagnostic on resolved synthetic observations only. No AP/ROC/operating threshold,
  release gate, retraining, drift promotion or business benefit is inferred from the toy set.
- Verify real accepted-model HTTP requests and journal persistence on synthetic inputs,
  including unauthenticated/invalid requests and journal failure. Simulate future outcomes
  with an explicit future reporting cutoff; mark all resulting quality figures synthetic.
  No prospective operational performance or source-data rights are established.

Production still requires authentic availability/correction history, population/operator/
usage acceptance, history storage, HTTPS/credential lifecycle, operating monitoring/load
and pilot acceptance. Private numerical reports and owner learning notes remain outside Git.


## Implemented verification

Synthetic contract tests cover authentication before input validation; server-generated IDs;
200/401/422/413/429/503 recording; privacy exclusions; fail-closed audit storage; canonical
retry/model separation; label maturity/censoring; availability/cutoff rejection; idempotency
and resolved-evidence conflicts. A real accepted-model HTTP run also exercised three toy
monthly contexts, exact retry deduplication and future positive/negative/censored outcomes.
Temporary processes are owned and stopped by the verification helper.

The reusable integration entrypoint is `python -m src.research.freddie_monitoring_demo` with
`--bundle`, `--token-file`, a fresh private `--output` and `--confirm-synthetic`. It creates
its own temporary loopback server, journal and separate random linking key; it does not use
or stop an existing server. Its optional `--assistant-check` distinguishes assistant runs.
The origin field is an assertion, not proof of the human operator's identity. Inputs, keys,
receipts and logs stay outside Git; a fresh output path is required for each execution.

Direct serving optionally accepts `--audit-db` on `src.research.freddie_shadow_api`. Default
serving without that flag remains compatible and reports `audit_enabled=false`. A ready
process alone does not verify an audit commit; the authenticated readiness request itself
must also pass its audit write. The schema is v1, with no automatic migration/overwrite of
an unrelated existing SQLite file. This journal is local and bounded, without rotation,
retention scheduling, multi-node storage or operational alert delivery.

At introduction, the container integration harness exercised the default serving mode. Native
journal verification does not establish persistent-volume journaling, backup/restore or
multi-worker behavior in a deployed container. These remain separate operating checks.


Local software validation on 20 October 2026: 341 tests passed, 4 skipped, 8 dependency deprecation
warnings. Black/isort/Ruff and mypy on 96 source files pass. Full unit-suite coverage rounds to 82%;
the journal module is 94%. The demo orchestration has no unit coverage in that suite and is
instead exercised separately against the actual accepted model. Real database/server and
container receipts remain private. Skipped optional integrations and uncovered failure/CLI
branches are not treated as production acceptance.


Follow-up20October2026: [the separate persistent-journal drill](FREDDIE_JOURNAL_RECOVERY.md)
now verifies a writable state bind mount, container replacement, unavailable-journal503,
online backup and fresh restore with committed scoring. It remains a same-host toy-context
drill; off-host recovery, scheduling/retention and actual operating acceptance remain open.
