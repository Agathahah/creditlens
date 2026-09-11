# CreditLens — engineering rules

- Read PROJECT_STATUS.md, docs/PRD.md, docs/DATA_DESIGN.md, docs/TECHNICAL_DESIGN.md, docs/EVALUATION_RELEASE_PLAN.md and docs/MILESTONES_ADR.md before implementation. Distinguish implemented behavior, historical evidence, and proposed designs.
- Public documentation and commit/PR descriptions describe project behavior, technical decisions, validation and limitations. Personal learning notes, exercises, interview preparation and conversation transcripts stay in the conversation and must not be committed or published.
- Current authorized implementation scope is M0 data diagnosis/recovery. M1–M5 implementation, full training, deployment and history rewriting require the relevant explicit authorization; document concrete criteria before those decisions.
- Check branch, HEAD, remote and local changes before work. Preserve unrelated changes, untracked files and existing human attribution. Never expose secrets or publish raw data/database backups.
- Use the verified repository-local Git identity. Do not automatically add AI author/co-author metadata. Preserve honest factual attribution of AI assistance without publishing personal session history.
- Use focused Conventional Commits and review changes in a PR. Do not merge, rewrite published history or force-push without explicit authorization.
- Prioritize label/time validity, train-only preprocessing, training-serving parity, model bundles, readiness, CI/release/rollback and monitoring. Do not claim production readiness from unit tests or hosting alone.
- Python public functions require type hints and Google-style docstrings. Follow black/isort/ruff/mypy and use meaningful contract tests. The historical 85% module coverage target is not currently enforced by CI; report actual coverage and gaps.
- PostgreSQL lineage is raw → staging → mart. Keep dbt contracts explicit: grain, keys, exclusions, labels and availability. Use a feature whitelist and keep test data out of model/threshold selection.
- Reproduce mutations on a private PostgreSQL cluster before applying schema/data recovery to the active database. Validate target, backup/restore, revision, disk capacity and row reconciliation; retain failure evidence.
- Make lint mutates files. Do not use make setup/load-data/dbt-run/lint/clean for read-only inspection. Makefile load-data currently lacks its mandatory --source argument.
- CLAUDE.md is historical project context; these rules supersede conflicting vendor/session workflow requirements.
- Four pre-existing *_CONTEXT.md files are local historical snapshots, not publication instructions.
- Graphify is only used when requested or explicitly authorized. For local checkout/commit, GRAPHIFY_SKIP_HOOK=1 uses the existing opt-out without deleting hooks.
- Ops Copilot requires a separate design after the core stabilizes. Start with evidence-based retrieval and bounded read-only tools; do not add swarm, Hermes, automatic retraining or credit decisions without an established requirement.
