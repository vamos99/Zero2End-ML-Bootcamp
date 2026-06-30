# Technical Audit Notes

## Findings

| Area | Finding | Action |
| --- | --- | --- |
| API | Dashboard and API contracts must stay aligned. | Keep endpoint tests near client changes. |
| Data | Local archive matches expected CSV count and headers. | Keep raw files local and run DB quality checks after ingest. |
| Documentation | Model results are prototype results, not measured business impact. | Keep README, RESULTS, model cards, notebooks, and dashboard scorecards aligned through `scripts/evaluate_olist_results.py`. |
| Repository layer | The broad repository layer has been split into action, ranking, logistics, customer, and executive modules with compatibility wrappers. | Keep facade delegation tests so legacy dashboard imports do not regress. |
| Queries | Some legacy dashboard helpers still mix SQL views and pandas transformations. | Prefer SQL filters and mart-backed calculations when touching those functions. |
| Exceptions | Some broad exceptions still return safe fallbacks. | Replace with logged exceptions in small scoped PRs where debugging value is high. |

## Completed Refactor Path

1. Extract action log functions.
2. Extract ranking functions.
3. Extract logistics functions.
4. Extract customer segment functions.
5. Extract executive, revenue, review, payment, cohort, and seller-SLA functions.
6. Keep compatibility wrappers in `src/database/repository.py`.
7. Add focused delegation tests before changing wrappers.

## Remaining Cleanup

1. Keep `get_total_orders`, `get_date_range`, and `get_generated_output_status`
   stable until dashboard imports are migrated or a small repository module is
   introduced for those root helpers.
2. Move additional broad pandas filtering into SQL only when changing the
   owning dashboard feature.
3. Keep the outcome scorecard, README, RESULTS, and notebook summaries synced
   after each measured-results script run.

## Guardrails

- Do not rewrite the repository layer in one PR.
- Do not mix SQL rewrites, feature work, and file movement.
- Keep Streamlit fallback schemas stable.
- Run CI after each small change.
