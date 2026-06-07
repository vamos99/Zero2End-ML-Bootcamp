import plotly.express as px
import streamlit as st


def _format_brl(value):
    return f"{value:,.0f} BRL"


def _metric_value(metrics, key, default=0):
    return metrics.get(key, default)


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

    row1 = st.columns(4)
    row1[0].metric("Orders", f"{total_orders:,}", help="Orders in the selected date range.")
    row1[1].metric("Product Revenue", _format_brl(total_revenue), help="Sum of item prices, excluding freight.")
    row1[2].metric("Avg. Order Value", _format_brl(avg_order_value), help="Product revenue divided by order count.")
    row1[3].metric("Customers", f"{unique_customers:,}", help="Unique customers in the selected date range.")

    row2 = st.columns(4)
    row2[0].metric(
        "Logistics Risk",
        f"{_metric_value(metrics, 'risk_logistics'):,} orders",
        help="Orders with a predicted delivery duration above the risk threshold.",
    )
    row2[1].metric(
        "Churn Risk Snapshot",
        f"{_metric_value(metrics, 'risk_churn'):,} customers",
        help="Current at-risk customer count from the segmentation output.",
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

    st.subheader("Recommended next checks")
    if _metric_value(metrics, "risk_logistics") > 0:
        st.warning("Operations: inspect delayed-order risk and prioritize customer communication.")
    else:
        st.success("Operations: no high-risk delivery backlog is visible for this window.")

    if _metric_value(metrics, "risk_churn") > 0:
        st.info("Customer: review the at-risk segment before launching retention actions.")
    else:
        st.info("Customer: segmentation outputs are needed for the churn-risk snapshot.")

    st.caption(
        "This overview is designed as a decision surface, not a full BI layer. "
        "Use the module pages for detailed drilldowns."
    )
