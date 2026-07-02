import plotly.express as px
import streamlit as st


def _format_brl(value):
    return f"{value:,.0f} BRL"


def _metric_value(metrics, key, default=0):
    return metrics.get(key, default)


def _format_pct(value):
    return f"{value:.1f}%"


def _format_count(value):
    return f"{value:,.0f}"


def _scorecard_markdown(rows):
    return "\n".join(
        (
            "- **{area}**: baseline `{baseline}`; current/target "
            "`{current_or_target}`; measured change `{measured_change}`; "
            "status `{status}`."
        ).format(
            area=row.get("area", ""),
            baseline=row.get("baseline", ""),
            current_or_target=row.get("current_or_target", ""),
            measured_change=row.get("measured_change", ""),
            status=row.get("status", ""),
        )
        for row in rows
    )


def _answer_cards_table(rows):
    if not rows:
        return None

    display_rows = []
    for row in rows:
        display_rows.append(
            {
                "Area": row.get("area", ""),
                "Type": row.get("result_type", ""),
                "Baseline": row.get("baseline", ""),
                "Current / target": row.get("current_or_target", ""),
                "Delta / change": row.get("delta_or_change", ""),
                "Boundary": row.get("boundary", ""),
            }
        )
    return display_rows


def _category_signal_table(category_performance):
    if category_performance is None or category_performance.empty:
        return None

    display_columns = [
        "category",
        "orders",
        "product_revenue",
        "avg_review_score",
        "late_delivery_rate",
    ]
    return category_performance[display_columns].rename(
        columns={
            "category": "Category",
            "orders": "Orders",
            "product_revenue": "Product revenue",
            "avg_review_score": "Avg. review",
            "late_delivery_rate": "Late delivery",
        }
    )


def _location_lane_table(location_service_levels):
    if location_service_levels is None or location_service_levels.empty:
        return None

    display_df = location_service_levels.copy()
    display_df["Lane"] = (
        display_df["seller_state"].astype(str) + " -> " + display_df["customer_state"].astype(str)
    )
    display_columns = [
        "Lane",
        "lane_type",
        "orders",
        "product_revenue",
        "avg_delivery_days",
        "late_delivery_rate",
    ]
    return display_df[display_columns].rename(
        columns={
            "lane_type": "Lane type",
            "orders": "Orders",
            "product_revenue": "Product revenue",
            "avg_delivery_days": "Avg. delivery days",
            "late_delivery_rate": "Late delivery",
        }
    )


def render_home_view(metrics, executive_data=None):
    executive_data = executive_data or {}

    st.title("Executive Analytics Overview")
    st.caption(
        "A compact view of marketplace health: demand, revenue, customer risk, and delivery quality."
    )

    total_orders = _metric_value(metrics, "total_orders")
    total_revenue = _metric_value(metrics, "total_revenue")
    avg_order_value = _metric_value(metrics, "avg_order_value")
    unique_customers = _metric_value(metrics, "unique_customers")
    late_delivery_rate = _metric_value(metrics, "late_delivery_rate")
    avg_review_score = _metric_value(metrics, "avg_review_score")
    generated_outputs = metrics.get("generated_outputs", {})
    logistics_available = generated_outputs.get("logistics_predictions", False)
    segments_available = generated_outputs.get("customer_segments", False)

    row1 = st.columns(4)
    row1[0].metric("Orders", f"{total_orders:,}", help="Orders in the selected date range.")
    row1[1].metric("Product Revenue", _format_brl(total_revenue), help="Sum of item prices, excluding freight.")
    row1[2].metric("Avg. Order Value", _format_brl(avg_order_value), help="Product revenue divided by order count.")
    row1[3].metric("Customers", f"{unique_customers:,}", help="Unique customers in the selected date range.")

    row2 = st.columns(4)
    row2[0].metric(
        "Logistics Risk",
        f"{_metric_value(metrics, 'risk_logistics'):,} orders" if logistics_available else "Not built",
        help="Orders with a predicted delivery duration above the risk threshold.",
    )
    row2[1].metric(
        "Churn Risk Snapshot",
        f"{_metric_value(metrics, 'risk_churn'):,} customers" if segments_available else "Not built",
        help="Current relative At Risk profile count from the segmentation output.",
    )
    row2[2].metric(
        "Late Delivery Rate",
        f"{late_delivery_rate:.1f}%",
        help="Delivered orders that arrived after the estimated date.",
    )
    row2[3].metric(
        "Avg. Review Score",
        f"{avg_review_score:.2f}",
        help="Average review score in the selected date range.",
    )

    st.markdown("---")

    impact_summary = executive_data.get("impact_summary", {})
    source_baselines = impact_summary.get("source_baselines", {})
    delivery_source = source_baselines.get("delivery", {})
    repeat_source = source_baselines.get("repeat_purchase", {})
    delivery_scenario = impact_summary.get("delivery_scenario", {})
    repeat_scenario = impact_summary.get("repeat_purchase_scenario", {})

    if impact_summary:
        st.subheader("Baseline and scenario targets")
        st.caption(
            "These are source baselines and planning scenarios. They are not measured post-intervention impact."
        )
        scenario_cols = st.columns(4)
        scenario_cols[0].metric(
            "Source Late Rate",
            _format_pct(delivery_source.get("late_delivery_rate_pct", 0.0)),
            help="Full source snapshot late-delivery baseline.",
        )
        scenario_cols[1].metric(
            "10% Late Reduction Scenario",
            _format_pct(delivery_scenario.get("projected_late_rate_pct", 0.0)),
            delta=f"{delivery_scenario.get('late_rate_delta_pp', 0.0):.2f} pp",
            help="Scenario target if 10% of late deliveries are prevented.",
        )
        scenario_cols[2].metric(
            "Source Repeat Rate",
            _format_pct(repeat_source.get("repeat_customer_rate_pct", 0.0)),
            help="Full source snapshot repeat-customer baseline.",
        )
        scenario_cols[3].metric(
            "+1pp Repeat Scenario",
            _format_pct(repeat_scenario.get("projected_repeat_rate_pct", 0.0)),
            delta=f"+{_format_count(repeat_scenario.get('additional_repeat_customers', 0.0))} customers",
            help="Scenario target for a future controlled retention experiment.",
        )
        st.caption(impact_summary.get("boundary", "Scenario targets are not measured impact."))

        with st.expander("Scenario calculation details"):
            st.markdown(
                f"""
                | Scenario | Baseline | Projected | Operational quantity |
                | --- | ---: | ---: | ---: |
                | {delivery_scenario.get("assumption", "Late delivery scenario")} | {_format_pct(delivery_scenario.get("baseline_late_rate_pct", 0.0))} | {_format_pct(delivery_scenario.get("projected_late_rate_pct", 0.0))} | {_format_count(delivery_scenario.get("prevented_late_orders", 0.0))} orders / {_format_count(delivery_scenario.get("potential_late_days_avoided", 0.0))} late-days |
                | {repeat_scenario.get("assumption", "Repeat-customer scenario")} | {_format_pct(repeat_scenario.get("baseline_repeat_rate_pct", 0.0))} | {_format_pct(repeat_scenario.get("projected_repeat_rate_pct", 0.0))} | {_format_count(repeat_scenario.get("additional_repeat_customers", 0.0))} customers |
                """
            )

        outcome_scorecard = executive_data.get("outcome_scorecard", [])
        answer_cards = _answer_cards_table(executive_data.get("dashboard_answer_cards", []))
        if answer_cards:
            st.markdown("**Direct outcome answer cards**")
            st.caption(
                "Baseline, current or target value, numeric delta, and claim boundary. "
                "Rows marked as scenario are targets, not completed improvements."
            )
            st.dataframe(
                answer_cards,
                width="stretch",
                hide_index=True,
                column_config={
                    "Boundary": st.column_config.TextColumn(width="large"),
                    "Delta / change": st.column_config.TextColumn(width="medium"),
                },
            )

        if outcome_scorecard:
            st.markdown("**Measured outcome scorecard**")
            st.caption(
                "This table answers what changed: source baseline, scenario target, "
                "or measured impact. Business impact remains unmeasured unless stated."
            )
            st.markdown(_scorecard_markdown(outcome_scorecard))

        st.markdown("---")

    st.subheader("Where performance is concentrated")
    col1, col2 = st.columns(2)

    revenue_by_state = executive_data.get("revenue_by_state")
    with col1:
        st.markdown("**Revenue by customer state**")
        if revenue_by_state is not None and not revenue_by_state.empty:
            fig = px.bar(
                revenue_by_state,
                x="customer_state",
                y="revenue",
                color="order_count",
                labels={
                    "customer_state": "State",
                    "revenue": "Product revenue (BRL)",
                    "order_count": "Orders",
                },
                title="Top states by revenue",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Revenue distribution is available after the order tables are loaded.")

    review_delivery_matrix = executive_data.get("review_delivery_matrix")
    with col2:
        st.markdown("**Review score vs. delivery quality**")
        if review_delivery_matrix is not None and not review_delivery_matrix.empty:
            fig = px.scatter(
                review_delivery_matrix,
                x="review_score",
                y="late_delivery_rate",
                size="order_count",
                labels={
                    "review_score": "Review score",
                    "late_delivery_rate": "Late delivery rate (%)",
                    "order_count": "Orders",
                },
                title="Delivery risk by review score",
            )
            fig.update_xaxes(dtick=1)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Review and delivery diagnostics are available after review tables are loaded.")

    st.markdown("---")

    st.subheader("Executive operating signals")
    signal_col1, signal_col2 = st.columns(2)

    payment_mix = executive_data.get("payment_mix")
    with signal_col1:
        st.markdown("**Payment mix**")
        if payment_mix is not None and not payment_mix.empty:
            payment_mix = payment_mix.copy()
            total_payment_value = payment_mix["payment_value"].sum()
            payment_mix["payment_share"] = 0.0
            if total_payment_value:
                payment_mix["payment_share"] = payment_mix["payment_value"] / total_payment_value * 100
            fig = px.bar(
                payment_mix,
                x="payment_type",
                y="payment_value",
                color="orders",
                labels={
                    "payment_type": "Payment type",
                    "payment_value": "Payment value (BRL)",
                    "orders": "Orders",
                },
                title="Payment value by method",
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(
                payment_mix[["payment_type", "orders", "payment_share", "avg_installments"]]
                .rename(
                    columns={
                        "payment_type": "Payment type",
                        "orders": "Orders",
                        "payment_share": "Value share",
                        "avg_installments": "Avg. installments",
                    }
                )
                .style.format({"Orders": "{:,.0f}", "Value share": _format_pct, "Avg. installments": "{:.2f}"}),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Payment mix is available after SQL views are applied to the local database.")

    cohort_retention = executive_data.get("cohort_retention")
    with signal_col2:
        st.markdown("**Customer cohort retention**")
        if cohort_retention is not None and not cohort_retention.empty:
            heatmap_data = cohort_retention.pivot(
                index="cohort_month",
                columns="months_since_first_order",
                values="retention_rate",
            ).sort_index(ascending=False)
            fig = px.imshow(
                heatmap_data,
                aspect="auto",
                color_continuous_scale="Blues",
                text_auto=".1f",
                labels={
                    "x": "Months since first order",
                    "y": "Cohort month",
                    "color": "Retention %",
                },
                title="Retention by first-purchase cohort",
            )
            fig.update_layout(coloraxis_colorbar_ticksuffix="%")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Cohort retention is available after the cohort SQL mart is applied.")

    seller_sla_watchlist = executive_data.get("seller_sla_watchlist")
    st.markdown("**Seller SLA watchlist**")
    if seller_sla_watchlist is not None and not seller_sla_watchlist.empty:
        fig = px.scatter(
            seller_sla_watchlist,
            x="orders",
            y="late_delivery_rate",
            size="product_revenue",
            color="avg_review_score",
            hover_name="seller_label",
            labels={
                "orders": "Delivered orders",
                "late_delivery_rate": "Late delivery rate (%)",
                "product_revenue": "Product revenue (BRL)",
                "avg_review_score": "Avg. review score",
            },
            title="High-volume sellers with SLA risk",
        )
        st.plotly_chart(fig, width="stretch")

        display_columns = [
            "seller_label",
            "seller_state",
            "orders",
            "product_revenue",
            "avg_review_score",
            "avg_delivery_days",
            "late_delivery_rate",
        ]
        st.dataframe(
            seller_sla_watchlist[display_columns]
            .rename(
                columns={
                    "seller_label": "Seller",
                    "seller_state": "State",
                    "orders": "Orders",
                    "product_revenue": "Product revenue",
                    "avg_review_score": "Avg. review",
                    "avg_delivery_days": "Avg. delivery days",
                    "late_delivery_rate": "Late delivery",
                }
            )
            .style.format(
                {
                    "Orders": "{:,.0f}",
                    "Product revenue": "{:,.0f} BRL",
                    "Avg. review": "{:.2f}",
                    "Avg. delivery days": "{:.1f}",
                    "Late delivery": _format_pct,
                }
            ),
            width="stretch",
            hide_index=True,
        )
        st.caption("Seller SLA is a full-dataset view; the page date filter applies to order-window charts.")
    else:
        st.info("Seller SLA watchlist is available after SQL views are applied to the local database.")

    st.markdown("**Category and location service signals**")
    category_signal_col, location_signal_col = st.columns(2)

    category_performance = executive_data.get("category_performance")
    with category_signal_col:
        st.markdown("**Category revenue and quality**")
        category_table = _category_signal_table(category_performance)
        if category_table is not None:
            fig = px.bar(
                category_performance,
                x="category",
                y="product_revenue",
                color="late_delivery_rate",
                labels={
                    "category": "Category",
                    "product_revenue": "Product revenue (BRL)",
                    "late_delivery_rate": "Late delivery (%)",
                },
                title="Top categories by product revenue",
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(
                category_table.style.format(
                    {
                        "Orders": "{:,.0f}",
                        "Product revenue": "{:,.0f} BRL",
                        "Avg. review": "{:.2f}",
                        "Late delivery": _format_pct,
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Category performance is available after SQL views are applied to the local database.")

    location_service_levels = executive_data.get("location_service_levels")
    with location_signal_col:
        st.markdown("**Location service lanes**")
        location_table = _location_lane_table(location_service_levels)
        if location_table is not None:
            lane_chart = location_table.copy()
            fig = px.bar(
                lane_chart,
                x="Lane",
                y="Orders",
                color="Late delivery",
                labels={
                    "Lane": "Seller -> customer state",
                    "Orders": "Delivered orders",
                    "Late delivery": "Late delivery (%)",
                },
                title="Highest-volume state lanes",
            )
            st.plotly_chart(fig, width="stretch")
            st.dataframe(
                location_table.style.format(
                    {
                        "Orders": "{:,.0f}",
                        "Product revenue": "{:,.0f} BRL",
                        "Avg. delivery days": "{:.1f}",
                        "Late delivery": _format_pct,
                    }
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Location service lanes are available after SQL views are applied to the local database.")

    with st.expander("Dashboard data sources"):
        st.markdown(
            """
            | Dashboard block | Source |
            | --- | --- |
            | Revenue by customer state | `orders`, `order_items`, `customers` |
            | Review score vs. delivery quality | `orders`, `order_reviews` |
            | Payment mix | `payment_mix_summary` |
            | Customer cohort retention | `customer_cohort_retention` |
            | Seller SLA watchlist | `seller_sla_summary` |
            | Category revenue and quality | `category_performance_summary` |
            | Location service lanes | `location_service_level_summary` |
            """
        )

    st.markdown("---")

    st.subheader("Recommended next checks")
    if not logistics_available:
        st.info("Operations: build the logistics prediction output before interpreting delivery risk.")
    elif _metric_value(metrics, "risk_logistics") > 0:
        st.warning("Operations: inspect delayed-order risk and prioritize customer communication.")
    else:
        st.success("Operations: no high-risk delivery backlog is visible for this window.")

    if not segments_available:
        st.info("Customer: build the segmentation output before interpreting the At Risk snapshot.")
    elif _metric_value(metrics, "risk_churn") > 0:
        st.info("Customer: review the at-risk segment before launching retention actions.")
    else:
        st.info("Customer: no customers are currently labeled At Risk in the generated segment snapshot.")

    st.caption(
        "This overview is designed as a decision surface, not a full BI layer. "
        "Use the module pages for detailed drilldowns."
    )
