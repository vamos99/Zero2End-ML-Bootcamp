# Technical Audit Notes

This document records concrete engineering findings from the repository audit. It is limited to actionable maintenance work; exploratory product ideas are intentionally excluded.

## Current status

The project already has useful separation between API, dashboard views, services, SQL views, validation scripts and tests. The next improvements should focus on contract consistency, documentation accuracy and small refactors.

## Findings

| Area | Finding | Impact | Recommended action |
| --- | --- | --- | --- |
| API contract | Dashboard client expected a segment summary endpoint while the API only had a single-customer segment endpoint. | Client/API mismatch. | Add a small read-only summary endpoint and test coverage. |
| API security | Inference endpoints now use the existing API key dependency. | README and runtime behavior are aligned. | Keep root and health public; keep inference protected. |
| Data validation | Uploaded Olist archive matches the expected raw CSV contract. | Local validation can proceed without committing raw data. | Keep raw files local and run DB/quality checks after ingestion. |
| Model documentation | Model outputs are prototype results and need limitations close to the code. | Reduces overclaiming risk. | Maintain `docs/MODEL_CARD.md`. |
| Repository module size | `src/database/repository.py` mixes executive metrics, logistics, segmentation, action logs and ranking queries. | Harder to test and maintain; single file has multiple responsibilities. | Split by dashboard domain in small behavior-preserving PRs. |
| Query placement | Some functions fetch broad tables into pandas and filter in Python. | Acceptable for the bootcamp dataset, but not scalable. | Prefer SQL-side filtering for date windows and limits when touching those functions. |
| Exception handling | Several functions return empty defaults after broad exceptions. | UI stays stable but debugging becomes harder. | Replace bare `except` with logged `except Exception as exc` in small follow-up PRs. |

## Suggested refactor sequence

Do not rewrite the repository layer in one large PR. Use this order:

1. Extract action log functions into `src/database/action_repository.py`.
2. Extract ranking functions into `src/database/ranking_repository.py`.
3. Extract logistics functions into `src/database/logistics_repository.py`.
4. Extract customer segment functions into `src/database/customer_repository.py`.
5. Keep compatibility imports in `repository.py` until dashboard imports are migrated.
6. Add one focused test per extracted module before removing compatibility wrappers.

## Refactor guardrails

- No dashboard behavior change in extraction PRs.
- No SQL logic rewrite in the same PR as file movement.
- Keep PRs below a small reviewable size.
- Keep fallback DataFrame schemas stable so Streamlit pages do not break.
- Run the existing test suite after each PR.

## Deferred work

The following should not be started until the contract and documentation fixes are stable:

- Alternative recommender experiments.
- New optimization algorithms.
- Major dashboard redesign.
- Deployment hardening beyond the current local/portfolio scope.
