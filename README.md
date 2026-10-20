# CreditLens

CreditLens is a public-data credit-risk project covering PostgreSQL/dbt transformations, model evaluation, explainability, and a scoring API.

## Business problem and intended workflow

Updated20October2026. CreditLens studies **portfolio monitoring after disbursement**:
organize monthly loan histories, distinguish missing outcomes from observed non-events,
and evaluate whether risk ranking can help analysts prioritize a limited review workload.
Its engineering flow is source reconciliation → temporal data contracts → independent
model evaluation → verified serving artifacts → bounded API and recovery checks.

The public dashboard and Tableau describe the historical LendingClub portfolio. A separate
private Freddie Mac mortgage study tests a three-month deterioration target for active,
current loans. Mortgage evidence is not transferred to fintech applicants or used for
live lending decisions. No measured loss reduction or operational business return is claimed.

## Current status

| Component | Implemented evidence | Boundary |
|---|---|---|
| LendingClub warehouse | 2,260,668 records reconciled across raw/staging/two loan marts; scoped recovery verified | Historical accepted-loan population |
| Historical LendingClub M1 | Train-only temporal experiment; failed its model/operating gates | Rejected; consumed2015test; not served |
| Separate mortgage v4 | Passed locked development validation and one-shot independent research test | Private retrospective research;2020/2022tests consumed |
| Monthly adapter and API | Supplied-availability checks; batch/reload/HTTP parity on synthetic monthly input | Authentic operational timestamps/history store remain open |
| Research API container | Pinned software-only image; isolated accepted-bundle parity, invalid-input and restart/recovery verification | Local network-none synthetic workload; not public ingress or an operating SLO |
| Inference audit and delayed labels | Private request journal, retry deduplication and explicitly synthetic three-month outcome diagnostics | Real operational outcomes, central logging and prospective quality remain unverified |
| Journal persistence and recovery | Container replacement, online SQLite backup, key/row reconciliation, write-failure and corrupt-backup rejection | Same-host synthetic drill; off-host recovery, retention and operating acceptance remain open |
| Fintech production scoring | HOLD | Product/population/rights, real data availability and operating acceptance remain required |

The API candidate is unchanged by container verification. No new training, threshold selection
or independent test run is triggered by startup, client execution, CI or dashboard hosting.

- [Project status](PROJECT_STATUS.md)
- [Technical documentation](docs/README.md)
- [Data design](docs/DATA_DESIGN.md)
- [Evaluation and release plan](docs/EVALUATION_RELEASE_PLAN.md)
- [Next holdout decision](docs/M1_NEXT_HOLDOUT_DECISION.md)
- [Next experiment scope](docs/M1_NEXT_EXPERIMENT_SCOPE.md)
- [Local Docker guide](docs/LOCAL_DOCKER_GUIDE.md)
- [Tableau Public aggregate dashboard guide](docs/TABLEAU_PUBLIC_DASHBOARD_GUIDE.md)
- [Engineering rules](AGENTS.md)

Development has used AI assistance, including Claude and Codex. Technical claims are tied to source, tests, and recorded validation.

## CreditLens research dashboard

The dashboard explains the funded-loan portfolio, its outcome gaps, and the historical
model evidence behind a decision to hold scoring.
It presents 2,260,668 warehouse loans, explicit unresolved outcomes, vintage/term filters,
data lineage, historical model evaluation, API rejection contracts and dated Docker evidence.
Ten sections connect the business problem, descriptive dataset and models to the release decision. It reads only published aggregates;
there is no borrower upload, database connection or credit decision.

```bash
python -m streamlit run src/dashboard/app.py --server.address=127.0.0.1
```

Open http://localhost:8501 on the machine running the server. See the
[dashboard evidence and population definitions](docs/audit/DASHBOARD_DATA_STORY_2026-09-29.md),
[read-only aggregate queries](scripts/sql/dashboard_aggregates.sql), and
[packaging/public pilot runbook](docs/DASHBOARD_RELEASE_RUNBOOK.md).
The [public dashboard pilot](https://creditlens-risk-evidence.streamlit.app/) shows the
aggregate research story. Revision `084e524` passed dashboard CI and was checked on the public
URL on 30 September 2026. The historical LendingClub model remains below its gate. The pilot provides no
scoring API or credit decision; later source revisions require fresh public UI verification.

## Monthly mortgage research — separate from fintech scoring

The streaming monthly panel and three-month label preserve missing follow-up and termination
as censoring. The accepted v4 model is evaluated separately from the historical LendingClub
experiment. A timestamped monthly adapter and authenticated client have passed synthetic
batch/reload/HTTP parity. The [local container contract](docs/FREDDIE_CONTAINER_ACCEPTANCE.md)
adds isolated packaging, a small diagnostic workload and restart/recovery evidence. Corrected
source data still do not establish authentic point-in-time operational availability.
See [the monthly protocol](docs/FREDDIE_MONTHLY_RESEARCH_PROTOCOL.md) and
[adapter contract](docs/FREDDIE_MONTHLY_ADAPTER_CONTRACT.md).

[Tableau portfolio dashboard](https://public.tableau.com/app/profile/agatha.silalahi/viz/creditlens/CreditLensPortofoliodanBuktiModel)
was published on 6 October 2026; the owner confirmed it works on 7 October. This is a
historical aggregate exhibit, not a scoring-model release.

## Separate mortgage research — current service boundaries

Freddie v4 passed bounded development validation and a one-shot independent mortgage test.
A separate authenticated loopback API and monthly-record adapter verify offline/HTTP parity
with the private accepted candidate on synthetic requests. The same candidate also passes
isolated Docker serving/recovery checks. This does not promote LendingClub scoring or establish operational
fintech readiness. Models, source records, numeric mortgage reports and credentials remain
private. See [the v4 protocol](docs/FREDDIE_V4_HISTORY_PROTOCOL.md) and
[remaining service gates](docs/FREDDIE_NEXT_RESEARCH_AND_SERVICE.md).
