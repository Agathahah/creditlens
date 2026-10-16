# Private monthly-record adapter — implemented research contract

16 October 2026. This adapter extends the accepted v4 private mortgage research path.
It does not fit, recalibrate, select thresholds or reopen a source/test archive. Fintech
production scoring remains HOLD; source terms remain accepted for private research only.

## Data flow and boundary

`MonthlySnapshot` → supplied-availability selection → existing exact-calendar history
function → locked ordered 19-feature request → authenticated loopback `/ready` and `/score`.
The dedicated client sends only features; loan keys, records and supplied timestamps are
not sent to the scoring API or printed. The public dashboard does not load these files.

The input is a normalized single-loan domain snapshot, not an unvalidated SFLLD pipe file
or a live servicing feed. UPB is USD, interest/DTI/LTV values use percentage points, loan
age and remaining term use months, and delinquency is integer months (100 encodes REO).
Origination sentinel values follow the existing v4 protocol. Unknown status is NULL.

## Availability and identity rules

- Required timezone-aware prediction and availability timestamps; reporting periods are
  UTC calendar months and must be complete before their monthly records are available.
- Origination values must be available by prediction time. Monthly rows are restricted to
  the requested reporting month and its exact previous twelve months.
- Future reporting months and versions available after prediction are excluded. For each
  month, use the latest supplied version available by prediction time. Duplicate eligible
  month/availability pairs and mixed loan identities are rejected rather than guessed.
- An available current observation must be active, current, positive-balance and without
  a zero-balance/termination code. Calendar gaps or unknown prior statuses remain missing;
  completeness flags and all history formulas reuse the training implementation.
- The v4 protocol SHA is checked before deriving ordered features. No label/outcome field
  or arbitrary feature is accepted. Adapter calculations retain domain precision; the
  existing API applies the identical float32 model input conversion.

These are checks on **supplied timestamps**, not proof that the data were actually known
then. No timestamps are inferred from the corrected Freddie archive or assigned to real
loan records. There is no verified operator history store, ingestion correction log or
operational availability attestation. Synthetic parity cannot remove that limitation.

## Local client and access

`python -m src.research.freddie_monthly_client --snapshot <private JSON>
--token-file <private credential> --port <local port>` loads bounded owner-only files outside
Git. Snapshot size is limited to128KiB and256records; the token file is limited to4KiB.
Transport is fixed to literal127.0.0.1, never follows HTTP redirects, times out after10seconds
and checks authenticated readiness, consistent model identity, research scope, finite
probability and the3-month horizon. HTTP failures do not trigger an alternative endpoint.

Browser navigation to the protected API without its bearer token returns401. The API is
not a dashboard; use the authenticated client. Credentials are not placed in query strings
or browser storage. Request byte/rate limits remain the existing API contract.

## Verification and remaining work

Synthetic contract tests compare the adapter's float32 vector against the existing batch
training collector on a generated31/35-column archive. Tests also cover late corrections,
future invariance, calendar gaps/unknown values, ordering, ambiguous revisions, mixed IDs,
invalid times/types/domains/outcomes, sentinel handling, protocol changes, no identifier
transmission, no redirect following and rejecting API scope/version/output changes.

A real accepted-bundle loopback verification on synthetic monthly input matched offline
reload and HTTP probability exactly. The CLI also completed successfully. Numeric scores,
synthetic owner request, artifact hashes and receipt remain in private storage. This is
local synthetic integration evidence, not a repeated independent model evaluation.

Still required for an operational service: operator/product/rights acceptance, authentic
availability and correction history, a persistent versioned history store, image+bundle
parity, explicit load/SLO and resource evidence, HTTPS/credential lifecycle/audit events,
delayed-label monitoring and failure/rollback acceptance. No public scoring, hosting spend,
model redistribution or production readiness is established by this change.
