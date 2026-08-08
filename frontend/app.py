"""
app.py — Campus Router Health 360 Streamlit Dashboard
Frontend for monitoring campus router health, 24h metric analysis, user complaints, and AI copilot diagnostics.
"""

import os
import requests
import pandas as pd
import streamlit as st
import altair as alt

# ------------------------------------------------------------------------------
# Configuration & Setup
# ------------------------------------------------------------------------------
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="Campus Router Health 360",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern design and polished typography
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Header gradient banner */
    .header-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.3);
    }
    .header-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .header-subtitle {
        font-size: 1.05rem;
        color: #c7d2fe;
        margin-top: 6px;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        color: #f8fafc;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
        color: #f1f5f9;
    }
    
    /* Status Badges */
    .badge-bad {
        background-color: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        border: 1px solid rgba(239, 68, 68, 0.4);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-ok {
        background-color: rgba(34, 197, 94, 0.2);
        color: #86efac;
        border: 1px solid rgba(34, 197, 94, 0.4);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-warn {
        background-color: rgba(245, 158, 11, 0.2);
        color: #fde047;
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
    }

    /* Complaint Cards */
    .complaint-card {
        background-color: #0f172a;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .complaint-ticket {
        font-size: 0.8rem;
        color: #f87171;
        font-weight: 700;
    }
    .complaint-text {
        font-size: 0.95rem;
        color: #e2e8f0;
        margin-top: 4px;
    }
    .complaint-date {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 4px;
    }
    
    /* Copilot Output Container */
    .copilot-response {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 1px solid #4338ca;
        border-radius: 12px;
        padding: 20px;
        margin-top: 16px;
        color: #e0e7ff;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------------------
# Helper Functions for API Calls
# ------------------------------------------------------------------------------
@st.cache_data(ttl=15)
def fetch_rankings(n=10):
    try:
        resp = requests.get(f"{API_URL}/rankings?n={n}", timeout=5)
        if resp.status_code == 200:
            return resp.json().get("rankings", [])
        else:
            st.error(f"API Error {resp.status_code}: {resp.text}")
            return []
    except Exception as e:
        st.error(f"Could not connect to backend at `{API_URL}`: {e}")
        return []


def fetch_router_detail(router_id):
    try:
        resp = requests.get(f"{API_URL}/router/{router_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Failed to fetch details for router {router_id}: {resp.text}")
            return None
    except Exception as e:
        st.error(f"Error communicating with backend: {e}")
        return None


def call_copilot(router_id, question):
    try:
        resp = requests.post(
            f"{API_URL}/copilot",
            json={"router_id": router_id, "question": question},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Copilot API error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        st.error(f"Copilot request failed: {e}")
        return None


# ------------------------------------------------------------------------------
# Header Banner
# ------------------------------------------------------------------------------
st.markdown(
    """
<div class="header-banner">
    <div class="header-title">📡 Campus Router Health 360</div>
    <div class="header-subtitle">Fleet health monitoring, 24-hour telemetry diagnostics, and AI Copilot root cause resolution</div>
</div>
""",
    unsafe_allow_html=True,
)


# Sidebar Configuration & Refresh
with st.sidebar:
    st.markdown("### 📊 Fleet Rules & Thresholds")
    st.markdown("""
    - **Latency Threshold**: > 60 ms
    - **Packet Loss Threshold**: > 2.0 %
    - **Disconnects Threshold**: > 2 per hour
    - **Sustained Bad**: >= 5 bad hours / day
    """)
    st.markdown("---")
    if st.button("🔄 Refresh Telemetry Data"):
        st.cache_data.clear()
        st.rerun()


# ------------------------------------------------------------------------------
# Main Content: Rankings Table & Selection
# ------------------------------------------------------------------------------
rankings_data = fetch_rankings(10)

if not rankings_data:
    st.warning(
        f"⚠️ Unable to load router rankings. Please ensure the backend is running at `{API_URL}`."
    )
    st.stop()

rankings_df = pd.DataFrame(rankings_data)

# Fleet Summary Top Cards
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(
        """
    <div class="metric-card">
        <div class="metric-label">Worst-10 Routers</div>
        <div class="metric-value">10</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with c2:
    sustained_count = (
        int(rankings_df["sustained_bad"].sum())
        if "sustained_bad" in rankings_df
        else 0
    )
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Sustained Bad Routers</div>
        <div class="metric-value" style="color: #ef4444;">{sustained_count}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with c3:
    avg_score = (
        float(rankings_df["health_score"].mean())
        if "health_score" in rankings_df
        else 0
    )
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Avg Worst Health Score</div>
        <div class="metric-value" style="color: #f59e0b;">{avg_score:.1f}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
with c4:
    firmware_flagged = (
        rankings_df[rankings_df["firmware_version"] == "v5.1"]["router_id"].count()
        if "firmware_version" in rankings_df
        else 0
    )
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">v5.1 Firmware Routers</div>
        <div class="metric-value" style="color: #6366f1;">{firmware_flagged}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("### 🔴 Worst-10 Health Score Rankings")
st.markdown(
    "Click any row in the table below or select a router from the dropdown to inspect detailed telemetry, complaints, and AI diagnostics."
)

# Format Display Table
display_cols = [
    "router_id",
    "health_score",
    "bad_hour_count",
    "sustained_bad",
    "building",
    "room",
    "model",
    "firmware_version",
    "avg_latency_ms",
    "avg_packet_loss_pct",
]
available_cols = [col for col in display_cols if col in rankings_df.columns]

display_df = rankings_df[available_cols].copy()
display_df = display_df.rename(
    columns={
        "router_id": "Router ID",
        "health_score": "Health Score",
        "bad_hour_count": "Bad Hours (24h)",
        "sustained_bad": "Sustained Bad",
        "building": "Building",
        "room": "Room",
        "model": "Model",
        "firmware_version": "Firmware",
        "avg_latency_ms": "Avg Latency (ms)",
        "avg_packet_loss_pct": "Avg Loss (%)",
    }
)

router_ids = list(rankings_df["router_id"].unique())
if (
    "selected_router_id" not in st.session_state
    or st.session_state.selected_router_id not in router_ids
):
    st.session_state.selected_router_id = router_ids[0]

col_table, col_select = st.columns([3, 1])

with col_select:
    st.markdown("#### Select Router")
    selected_from_dropdown = st.selectbox(
        "Choose router:",
        options=router_ids,
        index=router_ids.index(st.session_state.selected_router_id)
        if st.session_state.selected_router_id in router_ids
        else 0,
        key="router_dropdown",
    )
    if selected_from_dropdown != st.session_state.selected_router_id:
        st.session_state.selected_router_id = selected_from_dropdown
        st.rerun()

with col_table:
    selection_event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="rankings_table",
    )

    if (
        selection_event
        and hasattr(selection_event, "selection")
        and selection_event.selection
        and "rows" in selection_event.selection
        and selection_event.selection["rows"]
    ):
        selected_row_idx = selection_event.selection["rows"][0]
        if 0 <= selected_row_idx < len(display_df):
            clicked_router_id = display_df.iloc[selected_row_idx]["Router ID"]
            if clicked_router_id != st.session_state.selected_router_id:
                st.session_state.selected_router_id = clicked_router_id
                st.rerun()

selected_router_id = st.session_state.selected_router_id
st.markdown("---")

# ------------------------------------------------------------------------------
# Detail Panel for Selected Router (GET /router/{router_id})
# ------------------------------------------------------------------------------
st.markdown(f"## 🔍 Detail Panel — Router `{selected_router_id}`")

detail_data = fetch_router_detail(selected_router_id)

if not detail_data:
    st.error(f"Could not load details for router {selected_router_id}.")
    st.stop()

info = detail_data.get("info", {})
score = detail_data.get("score", {})
metrics = detail_data.get("metrics", [])
complaints = detail_data.get("complaints", [])

# Router Overview Summary Card
d1, d2, d3, d4, d5 = st.columns(5)
with d1:
    h_score = score.get("health_score", 0)
    badge_class = (
        "badge-bad"
        if h_score < 60
        else ("badge-warn" if h_score < 75 else "badge-ok")
    )
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Health Score</div>
        <div class="metric-value">{h_score} <span class="{badge_class}">/ 100</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with d2:
    is_sustained = score.get("sustained_bad", False)
    status_label = "🚨 Sustained Bad" if is_sustained else "⚡ Isolated Spikes"
    badge_type = "badge-bad" if is_sustained else "badge-ok"
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Status</div>
        <div class="metric-value" style="font-size: 1.2rem;"><span class="{badge_type}">{status_label}</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with d3:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Location</div>
        <div class="metric-value" style="font-size: 1.2rem;">{info.get('building', 'N/A')} Rm {info.get('room', 'N/A')}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with d4:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Hardware & Firmware</div>
        <div class="metric-value" style="font-size: 1.2rem;">{info.get('model', 'N/A')} ({info.get('firmware_version', 'N/A')})</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with d5:
    st.markdown(
        f"""
    <div class="metric-card">
        <div class="metric-label">Bad Hours (24h)</div>
        <div class="metric-value" style="color: #f87171;">{score.get('bad_hour_count', 0)} / 24 hrs</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2 Charts: Latency (24h) & Packet Loss (24h)
# ------------------------------------------------------------------------------
st.markdown("### 📈 24-Hour Telemetry Performance Charts")

if metrics:
    metrics_df = pd.DataFrame(metrics)

    if "hour" in metrics_df.columns:
        metrics_df["hour_clean"] = metrics_df["hour"].apply(
            lambda x: str(x).split("T")[-1] if "T" in str(x) else str(x)
        )

    chart_col1, chart_col2 = st.columns(2)

    # Chart 1: Latency Over 24 Hours
    with chart_col1:
        st.markdown("#### ⏱️ Latency (ms) over 24 Hours")
        latency_chart = (
            alt.Chart(metrics_df)
            .mark_area(
                line={"color": "#f87171"},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="rgba(248, 113, 113, 0.4)", offset=0),
                        alt.GradientStop(color="rgba(248, 113, 113, 0.05)", offset=1),
                    ],
                    x1=0,
                    x2=0,
                    y1=1,
                    y2=0,
                ),
            )
            .encode(
                x=alt.X(
                    "hour_clean:O",
                    title="Hour of Day",
                    axis=alt.Axis(labelAngle=-45),
                ),
                y=alt.Y(
                    "latency_ms:Q", title="Latency (ms)", scale=alt.Scale(zero=True)
                ),
                tooltip=[
                    "hour_clean",
                    "latency_ms",
                    "avg_speed_mbps",
                    "signal_dbm",
                ],
            )
            .properties(height=320)
        )

        thresh_line1 = (
            alt.Chart(pd.DataFrame({"y": [60]}))
            .mark_rule(color="#ef4444", strokeDash=[4, 4], strokeWidth=2)
            .encode(y="y:Q")
        )

        st.altair_chart(latency_chart + thresh_line1, use_container_width=True)
        st.caption("🔴 Red dotted line indicates 60 ms bad latency threshold.")

    # Chart 2: Packet Loss Over 24 Hours
    with chart_col2:
        st.markdown("#### 📦 Packet Loss (%) over 24 Hours")
        packet_loss_chart = (
            alt.Chart(metrics_df)
            .mark_area(
                line={"color": "#fbbf24"},
                color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="rgba(251, 191, 36, 0.4)", offset=0),
                        alt.GradientStop(color="rgba(251, 191, 36, 0.05)", offset=1),
                    ],
                    x1=0,
                    x2=0,
                    y1=1,
                    y2=0,
                ),
            )
            .encode(
                x=alt.X(
                    "hour_clean:O",
                    title="Hour of Day",
                    axis=alt.Axis(labelAngle=-45),
                ),
                y=alt.Y(
                    "packet_loss_pct:Q",
                    title="Packet Loss (%)",
                    scale=alt.Scale(zero=True),
                ),
                tooltip=[
                    "hour_clean",
                    "packet_loss_pct",
                    "disconnects",
                    "connected_devices",
                ],
            )
            .properties(height=320)
        )

        thresh_line2 = (
            alt.Chart(pd.DataFrame({"y": [2.0]}))
            .mark_rule(color="#f59e0b", strokeDash=[4, 4], strokeWidth=2)
            .encode(y="y:Q")
        )

        st.altair_chart(packet_loss_chart + thresh_line2, use_container_width=True)
        st.caption("🟡 Amber dotted line indicates 2.0% bad packet loss threshold.")
else:
    st.info("No hourly metrics data available for this router.")

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Router Complaints List
# ------------------------------------------------------------------------------
st.markdown("### 📝 User Complaints History")

if complaints:
    st.markdown(
        f"Found **{len(complaints)}** complaint ticket(s) logged for router `{selected_router_id}`:"
    )
    comp_cols = st.columns(min(len(complaints), 3))
    for idx, comp in enumerate(complaints):
        col_target = comp_cols[idx % len(comp_cols)]
        with col_target:
            st.markdown(
                f"""
            <div class="complaint-card">
                <div class="complaint-ticket">🎟️ {comp.get('ticket_id', 'T-???')}</div>
                <div class="complaint-text">"{comp.get('complaint_text', '')}"</div>
                <div class="complaint-date">📅 Reported on: {comp.get('date', 'N/A')}</div>
            </div>
            """,
                unsafe_allow_html=True,
            )
else:
    st.success("✅ No user complaints filed for this router.")

st.markdown("---")

# ------------------------------------------------------------------------------
# Copilot Text Input Box & Execution (POST /copilot)
# ------------------------------------------------------------------------------
st.markdown(f"## 🤖 AI Diagnostic Copilot — Router `{selected_router_id}`")
st.markdown(
    "Ask the Copilot to analyze root cause, recommend physical vs firmware actions, or evaluate telemetry evidence."
)

# Quick prompt shortcuts
st.markdown("**Quick Prompts:**")
qp_cols = st.columns(3)
quick_question = None
with qp_cols[0]:
    if st.button("❓ Why is this router failing?", use_container_width=True):
        quick_question = "Why is this router failing and what is the root cause?"
with qp_cols[1]:
    if st.button("🛠️ What fix action is recommended?", use_container_width=True):
        quick_question = "What fix action is recommended for this router?"
with qp_cols[2]:
    if st.button("💻 Is this a fleet firmware issue?", use_container_width=True):
        quick_question = "Is this issue related to a fleet firmware bug?"

# Copilot text input form
with st.form("copilot_form", clear_on_submit=False):
    default_q = (
        quick_question
        if quick_question
        else f"Diagnose performance issues for router {selected_router_id}."
    )
    user_question = st.text_input(
        "Enter your question for the Copilot:",
        value=default_q,
        placeholder=f"e.g., Why does router {selected_router_id} have low health score?",
        key="copilot_input",
    )
    submit_copilot = st.form_submit_button("🚀 Ask Copilot", use_container_width=True)

if submit_copilot or quick_question:
    query_text = quick_question if quick_question else user_question
    with st.spinner(
        "Analyzing telemetry data and generating deterministic diagnosis..."
    ):
        copilot_result = call_copilot(selected_router_id, query_text)

    if copilot_result:
        phrased_ans = copilot_result.get("phrased_answer", "")
        diag_dict = copilot_result.get("diagnosis", {})
        evidence = diag_dict.get("evidence", {})
        cause = diag_dict.get("cause", "unknown")
        fix = diag_dict.get("fix", "none")
        confidence = diag_dict.get("confidence", 0.0)

        st.markdown(
            f"""
        <div class="copilot-response">
            <div style="font-size: 1.1rem; font-weight: 700; color: #818cf8; margin-bottom: 8px;">
                💬 Copilot Diagnosis & Answer:
            </div>
            <div style="font-size: 1.05rem; line-height: 1.6;">
                {phrased_ans}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("### 🔢 Deterministic Raw Evidence Numbers")

        ev_c1, ev_c2, ev_c3, ev_c4 = st.columns(4)
        with ev_c1:
            st.metric("Diagnosed Cause", str(cause).replace("_", " ").title())
        with ev_c2:
            st.metric("Recommended Fix", str(fix).upper())
        with ev_c3:
            st.metric("Diagnosis Confidence", f"{confidence * 100:.0f}%")
        with ev_c4:
            st.metric("Evidence Points", f"{len(evidence)} items")

        with st.expander(
            "📄 View Full Raw Evidence JSON (Deterministic Output)", expanded=True
        ):
            st.json(
                {
                    "router_id": selected_router_id,
                    "cause": cause,
                    "fix": fix,
                    "confidence": confidence,
                    "evidence": evidence,
                }
            )
