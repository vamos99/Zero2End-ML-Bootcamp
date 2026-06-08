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
| P1 | dashboard | Add date and segment filters to dashboard | Filters update cards and charts consistently. |
| P2 | ml | Add model card for delivery/churn prototypes | Model purpose, features, limits, and validation notes are documented. |
| P2 | docs | Add dashboard walkthrough screenshots | README shows the default executive view and key decision points. |

## Recently Done

| Area | Task | Evidence |
| --- | --- | --- |
| analytics | Add metric dictionary for executive KPIs | `olist-intelligence/sql/METRICS.md` |
| data-pipeline | Add SQL reconciliation smoke checks | `olist-intelligence/tests/test_sql_views.py` |
| ci | Add a small sample-data test fixture | SQLite fixture in `test_sql_views.py` |

## Sprint Plan

### Sprint 1 - Portfolio Baseline

- Executive dashboard
- SQL analytics layer
- CI and dependency hygiene

### Sprint 2 - Analytics Reliability

- Metric dictionary
- Reconciliation checks
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
