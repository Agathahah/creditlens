# Private mortgage research API — implemented contract

Updated15October2026. `src.research.freddie_shadow_api` is a separate loopback application
for the accepted v4 retrospective mortgage candidate. Public fintech scoring remains HOLD.
It does not change the existing LendingClub model readiness or predict/explain endpoints.

## Inputs, artifacts and responses

A trusted owner-created manifest outside Git binds the v4 protocol, candidate, validation
and independent-test reports, ordered19-feature schema, float32 and library versions.
Both research gate reports are checked before own trusted weights are loaded. This is
operator evidence, not a signed deployment attestation. Artifact deserialization is not
permitted for arbitrary remote/user models.

- CLI: explicit bundle/token-file, fixed host127.0.0.1 and configurable unprivileged port.
  Bundle/credential must be owner-only and outside the repository. Token is not printed.
- `GET /ready`: requires bearer authentication; reports `research_ready=true` alongside
  `production_scoring_release=HOLD`, `point_in_time_verified=false`, private scope and model ID.
- `POST /score`: requires the exact named feature object. Types are finite numeric/NULL;
  unknown/missing keys, booleans, domain ranges and contradictory history completeness are
  rejected. Conversion/order matches the train/test float32 path.
- Output: probability,3-month horizon,model ID and explicit private/production boundaries.
  No approved/denied/tier/credit-limit decision is produced.

Inputs are **engineered domain features**, not verified operational monthly records.
The timestamped history store and raw-record feature adapter remain required for service
acceptance. Public documentation does not contain the private manifest, token, weights,
source records, predictions or numerical mortgage reports.

## Access and resource boundaries

Auth precedes parsing, with constant-time comparison. Limits are8,192actual received body
bytes and60authenticated requests/minute/process (including readiness). Predictions are
serialized and limited to two native-library threads. No public API docs/openapi endpoints
or default access logs. Responses set no-store/nosniff; validation responses do not echo
feature values and handle NaN safely as422. These controls do not constitute HTTPS,
credential lifecycle, distributed quota, user-level authorization or a production audit log.

## Verified evidence

Synthetic contracts cover401/422/413/429, exact feature order/dtype, research/production
readiness distinction and rejecting a manifest that declares production readiness.
Real loopback HTTP with the accepted candidate and synthetic inputs matched offline/reload
probability and tested authenticated readiness, missing auth, invalid domain, oversized
payload and NaN. The temporary server was stopped afterward. No test archive was reopened
for this verification and no model/preprocessor/calibrator fitting occurred.

Software CI uses only fixtures. It does not distribute private artifacts or re-run the
real mortgage evaluation. Image/bundle operating parity, named environment/load/SLO,
raw-record availability, delayed-label monitoring and rollback still need separate evidence.
[The v4 protocol](FREDDIE_V4_HISTORY_PROTOCOL.md) and [service sequence](FREDDIE_NEXT_RESEARCH_AND_SERVICE.md)
state the evaluated population and remaining acceptance requirements.
