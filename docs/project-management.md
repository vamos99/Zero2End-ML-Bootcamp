# Project Management

This document keeps the portfolio project manageable in GitHub Issues and GitHub Projects without adding heavy process.

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
| P1 | analytics | Add metric dictionary for executive KPIs | Each KPI has source table/view, grain, formula, and caveat. |
| P1 | dashboard | Add date and segment filters to dashboard | Filters update cards and charts consistently. |
| P1 | data-pipeline | Add SQL reconciliation smoke checks | SQLite views reconcile against source CSV extracts. |
| P2 | ml | Add model card for delivery/churn prototypes | Model purpose, features, limits, and validation notes are documented. |
| P2 | ci | Add a small sample-data test fixture | CI can run without depending on full local datasets. |
| P2 | docs | Add dashboard walkthrough screenshots | README shows the default executive view and key decision points. |

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

Create a repository project named `Olist Analytics Portfolio Board`, add the fields above, then use the issue templates in `.github/ISSUE_TEMPLATE/` for new work.
