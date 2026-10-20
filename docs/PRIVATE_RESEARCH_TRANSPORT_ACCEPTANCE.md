# Private HTTPS and credential rotation acceptance

20 October 2026. Contract fixed before implementation. Bounded local transport/access tests
for the unchanged accepted model, synthetic monthly inputs and private journal only.

- Add paired private certificate/key support to the loopback-only API. Reject an incomplete,
  unsafe, oversized or mismatched pair before model loading. Preserve the existing HTTP
  compatibility mode and research scope; HTTPS does not authorize public scoring.
- The monthly client selects HTTPS only with an explicit owner-only CA file outside Git,
  using default certificate chain and IP/hostname validation. Keep literal127.0.0.1, bounded
  port/time/body and no redirects. Never use an unverified SSL context or skip TLS checks.
- Generate a short-lived self-signed test certificate with loopback IP SAN in a fresh private
  directory. The test client explicitly trusts this test certificate. This is not a public
  certificate, CA enrollment, trust-store installation or production certificate lifecycle.
- Verify the actual accepted model over authenticated native HTTPS and isolated Docker HTTPS.
  Native feature/bundle and HTTP/TLS probabilities must agree within1e-12. Runtime source,
  bundle, certificate and verification code must be bound to the private receipt.
- Require rejection with the wrong trust anchor and a certificate whose SAN does not match
  the loopback IP. Test plaintext cannot obtain a successful response from the TLS port.
  Observe the negotiated TLS version, requiring TLS1.2or1.3.
- Exercise restart-based rotation using fresh test-only bearer credentials. CredentialA must
  work before rotation, then fail401after restart with credentialB; B must work. Preserve
  journal rows and successful request IDs across this change. Never change the owner's
  existing credential, model, protocol or original evidence. Record the interruption; no
  seamless rotation, expiry, external identity provider or zero-downtime claim.
- Docker remains network-none, no published ports, non-root, read-only root/model/token/TLS
  mount, only the journal mount writable, bounded CPU/RAM/PIDs/tmpfs. The TLS private key and
  test credentials are runtime-only files, never image/CI inputs. Explicit readiness probes
  replace automatic HTTP healthchecks during this bounded drill; operational HTTPS probing
  needs its own deployment policy.
- Keep private certificates/keys/tokens/journal/logs/receipts and owner guidance outside Git.
  Remove only test-owned processes/containers. Retain failed evidence; require all checks
  before PASS. The operational pilot remains NOT_ADMITTED under the separate pilot contract.

Technical references: [Uvicorn SSL configuration](https://github.com/Kludex/uvicorn/blob/0.34.0/uvicorn/config.py),
[Python SSL client contexts](https://docs.python.org/3.12/library/ssl.html#ssl.create_default_context)
and [HTTPSConnection](https://docs.python.org/3.12/library/http.client.html#http.client.HTTPSConnection).


## Implemented local result

Actual accepted-model native and isolated Docker HTTPS passed with TLS1.3, exact synthetic
probability parity, wrong trust/hostname rejection and plaintext rejection. Restart-based
test credential replacement rejected the retired token401and accepted a new committed score;
earlier journal rows were unchanged. Original credentials, model and source archives were
not modified. HTTP compatibility and the previous persistence/recovery helper also passed
on the new software image. Private test keys and receipts stay outside Git.

Local suite:367passed,4skipped,8existing dependency warnings; Black/isort/Ruff and mypy96source
files pass, plus strict typing of four operations scripts. Unit coverage of src rounds to82%;
private API83%, monthly client60%, with CLI/error branches still uncovered. Native/Docker
orchestration is exercised separately from unit coverage. These figures do not admit an
operational pilot, public certificate/identity service, lender SLO or prospective model quality.

The bounded integration command is `python -m scripts.smoke_research_https` with explicit
`--image`, accepted private `--bundle`, declared synthetic `--snapshot`, fresh private
`--output` and `--confirm-synthetic`. Optional `--assistant-check` marks assistant execution;
the default origin is an unverified local command identity. It creates only test credentials
and local trust anchors, owns/cleans its temporary servers/containers and preserves evidence.
