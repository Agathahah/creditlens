# Isolated mortgage API container acceptance

19 October 2026. Authorized continuation is bounded local packaging and recovery verification
for the accepted private v4 mortgage research candidate. It does not authorize public
scoring, model redistribution, new model evaluation, source access or hosting expenditure.

## Acceptance contract fixed before execution

- Separate minimal image with pinned direct/transitive Python dependencies and public
  v4 protocol files. Model, numeric reports, token and source records never enter the build.
- Stage only the trusted candidate and its existing validation/test reports, a path-relocated
  owner manifest, and synthetic input into a fresh owner-only directory outside Git. No
  source ZIP or test predictions are staged; original artifacts are never modified.
- Record source tree/requirements hashes, base image digest, built image ID, artifact hashes
  and runtime versions. The runtime must match the admitted sklearn/numpy versions.
- Run as a non-root UID, root filesystem read-only, no capabilities, no new privileges,
  two CPUs,2GiB RAM, bounded PIDs/tmpfs and `--network none`. The API still binds127.0.0.1
  inside its network namespace. No host port or external network is opened. Probe with
  `docker exec` inside that namespace; this is not host-ingress or public TLS verification.
- Readiness/score return200, missing auth401, invalid feature422 and oversized body413.
  Synthetic monthly-record → feature → native reload → container HTTP probabilities must
  agree with absolute tolerance1e-12. No fitting or independent-source evaluation occurs.
- Diagnostic workload: two score warmups,12sequential requests and12requests at concurrency2.
  Report internal HTTP p50/p95/max, failures, model identity and process peak RSS. Keep the
  existing60authenticated requests/minute limit. This is a small diagnostic envelope, not
  a lender SLO, capacity benchmark or production performance acceptance.
- Stop only the test-owned instance; launch the same image with a separate manifest whose
  candidate checksum is deliberately wrong. It must exit nonzero without becoming ready.
  Restore the known image+good bundle and verify readiness and the identical synthetic
  probability. Record recovery time. This is local restart/recovery, not zero-downtime
  blue/green deployment or migration rollback.
- Always remove only containers created by this run. Preserve the image and private report;
  never prune unrelated resources, remove volumes or overwrite original evidence. Retain
  failure logs privately and do not print tokens/request bodies.

All criteria must be verified for a successful receipt. A failure retains private evidence
and prevents a PASS receipt. Source availability/correction evidence, operational rights,
operator/product fit, history store, external HTTPS/credential lifecycle, inference audit,
delayed-label monitoring and operating acceptance remain separate. Fintech scoring HOLD
and the consumed2020/2022test decisions are unchanged.

## Implemented result — 19 October 2026

The local accepted-bundle verification passed: exact native/container synthetic probability,
expected401/422/413responses, both diagnostic groups without failures, deliberate checksum
rejection and recovery on the known pair. Runtime/image/base/source/requirements/artifact
identity, process RSS, latency and recovery measurements are retained in the private receipt.
No test-owned containers remain. No source ZIP or independent test predictions were opened.

The new Research API Image Packaging CI job builds only public software/configuration and
verifies runtime pins, non-root/no-private-artifact image content and missing-bundle refusal.
It does not receive private weights, numerical reports or tokens; its PASS cannot substitute
for the separate real accepted-bundle local verification or an operating release decision.


## Follow-up — persistent journal recovery,20October2026

A [separate stateful acceptance drill](FREDDIE_JOURNAL_RECOVERY.md) exercises the same accepted
image with only a private journal bind mount writable. Earlier rows survive container
replacement; a temporarily unavailable journal holds scoring with503. Online backup plus
key/schema/logical validation restores into a fresh container/state directory and permits
committed scoring. The request after the backup is explicitly outside its recovery point.
No zero-loss, off-host failover, public ingress or production acceptance is claimed.
