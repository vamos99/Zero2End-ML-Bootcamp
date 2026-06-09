# Project Management

This document keeps the portfolio project manageable in GitHub Issues and GitHub Projects without adding heavy process.

## Live Board

- GitHub Project: https://github.com/users/vamos99/projects/3

## Workflow

Use a GitHub Projects board with these fields:

| Field | Values |
| --- | --- |
| Status | Backlog, Ready, In Progress, Review, Done |
| Priority | P0, P1, P2 |
| Area | analytics, dashboard, data-pipeline, ml, docs, ci |
| Size | S, M, L |
| Sprint | Sprint 1, Sprint 2, Sprint 3 |

Recommended board columns:

1. Backlog: useful ideas, not yet scoped.
2. Ready: scoped tasks with acceptance criteria.
3. In Progress: one or two active tasks only.
4. Review: PR opened, checks passing or under review.
5. Done: merged or intentionally closed.

## Definition of Ready

- The issue states the user-facing or analytical outcome.
- Data source and metric grain are named.
- Acceptance criteria include a verification step.
- Secrets, private data, and deployment assumptions are explicit.

## Definition of Done

- Code or documentation is committed on a feature branch.
- Relevant checks pass locally or in CI.
- Dashboard or SQL numbers reconcile with the selected source.
- README, runbook, or SQL docs are updated when the behavior changes.
- PR summary includes what changed and how it was verified.

## Current Backlog

| Priority | Area | Task | Acceptance Criteria |
| --- | --- | --- | --- |
| P1 | analytics | Add payment mix and review-delivery SQL marts | Views reconcile on a small fixture and document grain caveats. |
| P1 | analytics | Add cohort/retention foundation using `customer_unique_id` | Cohort logic uses customer identity correctly and is covered by tests. |
| P1 | dashboard | Map executive dashboard charts to SQL marts | README or docs show which mart powers each manager-facing chart. |
| P2 | ml | Add model card for delivery/churn prototypes | Model purpose, features, limits, leakage risks and validation notes are documented. |
| P2 | docs | Add dashboard walkthrough screenshots after real data QA | README shows key decision points only after local data/browser verification. |

## Recently Done

| Area | Task | Evidence |
| --- | --- | --- |
| analytics | Add metric dictionary for executive KPIs | `olist-intelligence/sql/METRICS.md` |
| data-pipeline | Add SQL reconciliation smoke checks | `olist-intelligence/tests/test_sql_views.py` |
| data-pipeline | Add Kaggle source schema contract | `olist-intelligence/src/data_contract.py` |
| data-pipeline | Add stable DB data-quality checks | `olist-intelligence/tests/test_data_contract.py` |
| ci | Add small sample-data test fixtures | SQLite fixtures in `test_sql_views.py` and `test_data_contract.py` |

## Sprint Plan

### Sprint 1 - Portfolio Baseline

- Executive dashboard
- SQL analytics layer
- CI and dependency hygiene

### Sprint 2 - Analytics Reliability

- Metric dictionary
- Reconciliation checks
- Source contract and data-quality checks
- Small test fixtures

### Sprint 3 - ML/MLOps Readiness

- Model card
- Prediction monitoring notes
- Batch scoring runbook

## Labels

- `type: task`, `type: bug`, `type: docs`
- `area: analytics`, `area: dashboard`, `area: data-pipeline`, `area: ml`, `area: ci`
- `priority: P0`, `priority: P1`, `priority: P2`

## GitHub Projects Setup

The project board already exists. Keep future issues small and link PRs back to
the board items when implementation starts.
