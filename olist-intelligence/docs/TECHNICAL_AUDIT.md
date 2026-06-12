# Technical Audit Notes

This document records concrete engineering findings from the repository audit. It excludes exploratory product ideas.

## Findings

| Area | Finding | Recommended action |
| --- | --- | --- |
| API | Dashboard and API contracts must stay aligned. | Keep endpoint tests near client changes. |
| Data | Local archive matches the expected CSV count and headers. | Keep raw files local and run DB quality checks after ingest. |
| Documentation | Model results are prototype results. | Keep limitations close to the README. |
| Repository layer | `src/database/repository.py` has multiple responsibilities. | Split by dashboard domain in small PRs. |
| Queries | Some functions filter broad pandas frames. | Prefer SQL filters when touching those functions. |
| Exceptions | Some broad exceptions hide debugging context. | Replace with logged exceptions in small PRs. |

## Suggested refactor order

1. Extract action log functions.
2. Extract ranking functions.
3. Extract logistics functions.
4. Extract customer segment functions.
5. Keep compatibility imports until dashboard imports are migrated.
6. Add focused tests before removing wrappers.

## Guardrails

- Do not rewrite the repository layer in one PR.
- Do not mix SQL logic rewrites with file movement.
- Keep fallback schemas stable for Streamlit pages.
- Run CI after each small change.
