# Bounded private HTTPS service acceptance

20 October 2026. Contract recorded before execution. This closes the remaining local
concurrency/rate-window diagnostic for the unchanged accepted mortgage research model.
It does not admit an operational pilot or define a lender service-level objective (SLO).

## Fixed workload and acceptance

- Use the current source-bound software image, accepted v4 bundle and explicitly synthetic
  monthly input. Fresh test credential/certificate and journal stay outside Git. No fitting,
  source archive access, consumed-test reopening or changes to the60requests/minute limit.
- Isolated Docker only: no network/published ports, non-root, two CPUs,2GiB memory, bounded
  PIDs/tmpfs, read-only root/model/certificate/token, private journal as the sole writable mount.
- Verify trusted loopback HTTPS readiness with audit enabled, two score warmups, then12scores
  sequentially and12at concurrency5. All scores must match native parity within1e-12 and
  preserve the research scope. Record end-to-end internal HTTPS times including handshake,
  response read and audit commit, plus API-process peak RSS. Report sample counts and empirical
  nearest-rank percentiles;24observations do not establish tail latency, capacity or uptime.
- Fill the unchanged authenticated quota within one real60-second window, requiring exactly
  60admitted requests including readiness and warmups. Require five further authenticated
  requests to return429without a probability and an unauthenticated request to return401.
  If the fill takes60seconds, fail the diagnostic rather than alter the rate limit.
- Wait a real61seconds after the fill, without replacing the process or resetting its clock.
  The next authenticated score must return200with the unchanged probability and a committed
  request ID. Deadline180seconds for container execution; retain failure evidence.
- Reconcile every returned request ID, status and successful probability with the private
  journal. Require unique IDs, no probability on rejected events, integrity checks and matching
  model identity. Preserve prior TLS/credential/recovery evidence, and remove only this run's
  uniquely labeled container. No public endpoint, load generator, credential or raw data export.

## Completion boundary

Publish only the engineering result and limits. Detailed timings, model outputs, credentials,
certificates/keys, logs, journal and owner instructions remain private. An independent operational
source/operator, original availability/correction history, mature real outcomes, public ingress/
identity, off-host encrypted recovery, retention and environment/load acceptance remain required.
Operational pilot remains NOT_ADMITTED and production scoring remains HOLD regardless of this
local result. Research acceptance, CI software acceptance and operational admission are separate.

## Technical basis

The probe uses a separate verified HTTPS connection per request and an unchanged shared
SSLContext. Python documents safe sharing of contexts between connections when configuration
is not changed after use. Concurrency is explicitly bounded with ThreadPoolExecutor; elapsed
intervals use a monotonic clock, without mocking/resetting the serving clock.

- [Python SSLContext](https://docs.python.org/3.12/library/ssl.html#ssl.SSLContext)
- [Python ThreadPoolExecutor](https://docs.python.org/3.12/library/concurrent.futures.html#concurrent.futures.ThreadPoolExecutor)
- [Python monotonic clock](https://docs.python.org/3.12/library/time.html#time.monotonic)

## Executed result

The final source-bound real-model run passed both12-request groups with no unexpected
failures, five expected429responses and one401. Exactly60authenticated requests including
readiness were admitted before quota refusal. The same process accepted a new score after
more than61seconds of actual waiting. All66observed response IDs/statuses/probabilities and
model identity reconciled with committed journal events. Test-owned container cleanup passed;
original credentials, model and prior journals were unchanged. Timings/RSS and raw receipts
remain private. These small empirical percentile samples are not tail-performance claims.

Local checks:376passed,4skipped,8existing dependency warnings; Black/isort/Ruff and mypy
96source files pass, plus explicit script typing. The configured src coverage is82% including
src test modules; implementation-only coverage excluding those modules is77.63%(3175/4090
statements). CLI/failure paths and standalone orchestration remain incompletely covered;
the real accepted-model integration is checked separately. Skipped online-store/optional
survival tests are not evidence of operational integration.
