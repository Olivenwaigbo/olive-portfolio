import re
from html import escape

import altair as alt
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="PayResolve",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# COLOUR PALETTE (white and purple)
# ============================================================

PURPLE = "#7C3AED"
DEEP_PURPLE = "#4C1D95"
MUTED = "#6B6784"

# Darkest purple = most severe
SEVERITY_RAMP = ["#4C1D95", "#6D28D9", "#8B5CF6", "#C4B5FD", "#DDD6FE"]

STATUS_ORDER = ["SUCCESS", "FAILED", "PENDING", "REVERSED"]
PRIORITY_ORDER = ["P1", "P2", "P3", "P4", "NONE"]
LEVEL_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]


# ============================================================
# HTML HELPERS
# ============================================================
# Streamlit runs st.markdown() through a Markdown parser first.
# Markdown treats any line indented by 4+ spaces as a code block,
# and a blank line ends an HTML block. That is why indented HTML
# was printed as raw text. render_html() strips the indentation and
# blank lines so each snippet is treated as one HTML block.


def render_html(markup, target=st):
    cleaned = "\n".join(
        line.strip()
        for line in markup.strip().splitlines()
        if line.strip()
    )
    target.markdown(cleaned, unsafe_allow_html=True)


def format_text(value):
    """
    Turn AI output (light Markdown) into safe HTML.
    Supports **bold**, headings, bullet lists and numbered lists.
    All text is escaped first, so it cannot inject HTML.
    """

    if value is None:
        return ""

    def inline(text):
        text = escape(text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return text.replace("$", "&#36;")

    parts = []
    list_tag = None

    def close_list():
        nonlocal list_tag
        if list_tag:
            parts.append(f"</{list_tag}>")
            list_tag = None

    for raw_line in str(value).replace("\r\n", "\n").splitlines():
        line = raw_line.strip()

        if not line:
            close_list()
            continue

        heading = re.match(r"^#{1,4}\s+(.*)$", line)
        bullet = re.match(r"^[-•*]\s+(.*)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.*)$", line)

        if heading:
            close_list()
            parts.append(
                f'<div class="ai-heading">{inline(heading.group(1))}</div>'
            )

        elif bullet or numbered:
            wanted = "ul" if bullet else "ol"

            if list_tag != wanted:
                close_list()
                parts.append(f"<{wanted}>")
                list_tag = wanted

            match = bullet or numbered
            parts.append(f"<li>{inline(match.group(1))}</li>")

        else:
            close_list()
            parts.append(f"<p>{inline(line)}</p>")

    close_list()

    return "".join(parts)


def text_or(value, default="—"):
    if value is None:
        return default

    if isinstance(value, float) and pd.isna(value):
        return default

    text = str(value)

    return text if text else default


def naira(value):
    try:
        return f"₦{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def status_badge(status):
    label = text_or(status, "UNKNOWN").upper()

    if label in {"SUCCESS", "SUCCESSFUL", "COMPLETED", "SETTLED"}:
        css_class = "badge-success"
    elif label in {"FAILED", "FAILURE", "ERROR", "TIMEOUT"}:
        css_class = "badge-failed"
    elif label in {"PENDING", "INITIATED", "PROCESSING"}:
        css_class = "badge-pending"
    elif label == "REVERSED":
        css_class = "badge-reversed"
    else:
        css_class = "badge-default"

    return f'<span class="status-badge {css_class}">{escape(label)}</span>'


def format_value(column, value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"

    if column == "amount":
        return naira(value)

    if column == "anomaly_score":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)

    if column == "potential_duplicate":
        return "Yes" if str(value).lower() in {"true", "1", "yes"} else "No"

    return str(value)


def section(title, description=None):
    sub = (
        f'<div class="section-sub">{escape(description)}</div>'
        if description
        else ""
    )

    render_html(
        f"""
        <div class="section">
            <div class="section-title">{escape(title)}</div>
            {sub}
        </div>
        """
    )


def subsection(title):
    render_html(f'<div class="sub-title">{escape(title)}</div>')


def chart_title(title, subtitle=None):
    sub = (
        f'<div class="chart-sub">{escape(subtitle)}</div>'
        if subtitle
        else ""
    )

    render_html(
        f"""
        <div class="chart-title">{escape(title)}</div>
        {sub}
        """
    )


def kpi_card(label, value_html, small=False):
    """value_html must already be safe (escaped) HTML."""

    size = " kpi-value-sm" if small else ""

    render_html(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{escape(label)}</div>
            <div class="kpi-value{size}">{value_html}</div>
        </div>
        """
    )


def rank_order(values, preferred):
    rank = {name: index for index, name in enumerate(preferred)}

    return sorted(
        values,
        key=lambda v: (rank.get(str(v).upper(), len(preferred)), str(v)),
    )


def unique_values(df, column):
    if column not in df.columns:
        return []

    return sorted(df[column].dropna().astype(str).unique())


# ============================================================
# CHART HELPER
# ============================================================


def bar_chart(
    df,
    category,
    value="count",
    order=None,
    horizontal=False,
    severity=False,
    height=300,
):
    if order is None:
        order = df.sort_values(value, ascending=False)[category].tolist()

    if severity:
        color = alt.Color(
            f"{category}:N",
            scale=alt.Scale(domain=order, range=SEVERITY_RAMP),
            legend=None,
        )
    else:
        color = alt.value(PURPLE)

    if horizontal:
        chart = alt.Chart(df).mark_bar(
            cornerRadiusTopRight=5,
            cornerRadiusBottomRight=5,
            size=18,
        ).encode(
            x=alt.X(f"{value}:Q", title=None),
            y=alt.Y(
                f"{category}:N",
                sort=order,
                title=None,
                axis=alt.Axis(labelLimit=280),
            ),
            color=color,
            tooltip=[category, value],
        )
    else:
        chart = alt.Chart(df).mark_bar(
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5,
            size=40,
        ).encode(
            x=alt.X(
                f"{category}:N",
                sort=order,
                title=None,
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(f"{value}:Q", title=None),
            color=color,
            tooltip=[category, value],
        )

    chart = (
        chart.properties(height=height)
        .configure_view(strokeWidth=0)
        .configure_axis(
            domain=False,
            ticks=False,
            gridColor="#F0EAFD",
            labelColor=MUTED,
            labelFontSize=12,
        )
    )

    st.altair_chart(chart, width="stretch")


# ============================================================
# API FUNCTIONS
# ============================================================


@st.cache_data(ttl=30)
def get_summary():
    response = requests.get(f"{API_URL}/summary", timeout=15)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_transactions(
    status=None,
    provider=None,
    incident_type=None,
    limit=500,
):
    params = {"limit": limit}

    if status:
        params["status"] = status

    if provider:
        params["provider"] = provider

    if incident_type:
        params["incident_type"] = incident_type

    response = requests.get(
        f"{API_URL}/transactions",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_incidents(priority=None, incident_type=None, limit=500):
    params = {"limit": limit}

    if priority:
        params["priority"] = priority

    if incident_type:
        params["incident_type"] = incident_type

    response = requests.get(
        f"{API_URL}/incidents",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_anomalies(level=None, limit=500):
    params = {"limit": limit}

    if level:
        params["level"] = level

    response = requests.get(
        f"{API_URL}/anomalies",
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_transaction(transaction_id):
    response = requests.get(
        f"{API_URL}/transactions/{transaction_id}",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30)
def get_transaction_timeline(transaction_id):
    response = requests.get(
        f"{API_URL}/transactions/{transaction_id}/timeline",
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def generate_ai_investigation(transaction_id):
    """
    Trigger an on-demand AI investigation.

    This is intentionally NOT cached because it is a
    POST request that creates/updates an investigation.
    """

    response = requests.post(
        f"{API_URL}/transactions/{transaction_id}/ai-investigation",
        timeout=90,
    )
    response.raise_for_status()
    return response.json()


# ============================================================
# CUSTOM CSS
# ============================================================

render_html(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    .stApp {
        background-color: #ffffff;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif;
        color: #1E1B2E;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    footer {
        visibility: hidden;
    }

    .block-container {
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    /* ---------- Sidebar ---------- */

    [data-testid="stSidebar"] {
        background-color: #FAF7FF;
        border-right: 1px solid #E6DCFB;
    }

    .brand {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #4C1D95;
    }

    .brand-sub {
        color: #6B6784;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-top: 0.3rem;
    }

    /* ---------- Buttons and inputs ---------- */

    .stApp .stButton > button {
        background-color: #7C3AED;
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.55rem 1rem;
        min-height: 44px;
    }

    .stApp .stButton > button p {
        color: #ffffff;
    }

    .stApp .stButton > button:hover {
        background-color: #6D28D9;
    }

    .stApp [data-baseweb="select"] > div {
        border-radius: 10px;
        border-color: #E6DCFB;
    }

    .stApp [data-baseweb="select"] > div:focus-within {
        border-color: #7C3AED;
        box-shadow: 0 0 0 1px #7C3AED;
    }

    .stApp label p {
        color: #1E1B2E;
        font-weight: 500;
    }

    /* ---------- Hero ---------- */

    .stApp .hero {
        background: #4C1D95;
        border-radius: 20px;
        padding: 2.2rem 2.4rem;
        margin-bottom: 1.6rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        gap: 1.5rem;
        flex-wrap: wrap;
    }

    .stApp .hero-title {
        color: #ffffff;
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -0.035em;
        line-height: 1.1;
    }

    .stApp .hero-sub {
        color: #DDD0FB;
        font-size: 1.02rem;
        line-height: 1.6;
        max-width: 44rem;
        margin: 0.6rem 0 0 0;
    }

    .stApp .hero-pill {
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.28);
        color: #ffffff;
        padding: 0.4rem 0.95rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    .stApp .hero-pill::before {
        content: "";
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #86EFAC;
        margin-right: 0.5rem;
    }

    /* ---------- Headings ---------- */

    .stApp .section {
        margin-top: 2.4rem;
        margin-bottom: 1rem;
    }

    .stApp .section-title {
        border-left: 4px solid #7C3AED;
        padding-left: 0.8rem;
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: #1E1B2E;
    }

    .stApp .section-sub {
        padding-left: calc(0.8rem + 4px);
        color: #6B6784;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }

    .stApp .sub-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #4C1D95;
        margin: 1.8rem 0 0.8rem 0;
    }

    .stApp .chart-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1E1B2E;
    }

    .stApp .chart-sub {
        font-size: 0.8rem;
        color: #6B6784;
        margin-top: 0.1rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #E6DCFB !important;
        border-radius: 14px;
    }

    /* ---------- KPI cards ---------- */

    .stApp .kpi-card {
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-left: 4px solid #7C3AED;
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        min-height: 104px;
    }

    .stApp .kpi-label {
        color: #6B6784;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 0.45rem;
    }

    .stApp .kpi-value {
        color: #4C1D95;
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }

    .stApp .kpi-value-sm {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0;
        line-height: 1.4;
        word-break: break-word;
    }

    /* ---------- Badges ---------- */

    .stApp .status-badge {
        display: inline-block;
        padding: 0.18rem 0.7rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 700;
        white-space: nowrap;
    }

    .stApp .badge-success { background: #DCFCE7; color: #166534; }
    .stApp .badge-failed { background: #FEE2E2; color: #991B1B; }
    .stApp .badge-pending { background: #FEF3C7; color: #92400E; }
    .stApp .badge-reversed { background: #EDE9FE; color: #5B21B6; }
    .stApp .badge-default { background: #F3EEFF; color: #5B21B6; }

    /* ---------- Transaction header and details ---------- */

    .stApp .txn-head {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin: 1.2rem 0 1rem 0;
    }

    .stApp .txn-id {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1E1B2E;
    }

    .stApp .txn-note {
        color: #6B6784;
        font-size: 0.85rem;
    }

    .stApp .detail-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: 0.75rem;
    }

    .stApp .detail {
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-radius: 12px;
        padding: 0.75rem 0.95rem;
    }

    .stApp .detail-wide {
        grid-column: 1 / -1;
    }

    .stApp .detail-label {
        color: #6B6784;
        font-size: 0.75rem;
    }

    .stApp .detail-value {
        color: #1E1B2E;
        font-weight: 600;
        font-size: 0.95rem;
        margin-top: 0.15rem;
        word-break: break-word;
    }

    /* ---------- Timeline ---------- */

    .stApp .timeline {
        margin: 0.4rem 0 0 0.6rem;
        padding-left: 1.6rem;
        border-left: 2px solid #E6DCFB;
    }

    .stApp .tl-item {
        position: relative;
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.9rem;
    }

    .stApp .tl-item::before {
        content: "";
        position: absolute;
        box-sizing: border-box;
        left: calc(-1.6rem - 8px);
        top: 1.05rem;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        background: #7C3AED;
        border: 3px solid #ffffff;
    }

    .stApp .tl-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }

    .stApp .tl-event {
        font-weight: 700;
        color: #1E1B2E;
    }

    .stApp .tl-meta {
        color: #6B6784;
        font-size: 0.82rem;
        margin-top: 0.35rem;
    }

    .stApp .tl-meta span {
        margin-right: 1.2rem;
    }

    /* ---------- AI investigation ---------- */

    .stApp .gen-card {
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.9rem;
        line-height: 1.6;
    }

    .stApp .gen-card p {
        margin: 0.4rem 0 0 0;
    }

    .stApp .gen-card .muted {
        color: #6B6784;
        font-size: 0.88rem;
    }

    .stApp .ai-box {
        background: #F5F0FF;
        border: 1px solid #E6DCFB;
        border-left: 4px solid #7C3AED;
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        margin-top: 0.9rem;
        color: #1E1B2E;
        line-height: 1.7;
    }

    .stApp .ai-title {
        font-weight: 700;
        color: #4C1D95;
        margin-bottom: 0.6rem;
    }

    .stApp .ai-heading {
        font-weight: 700;
        color: #4C1D95;
        margin: 1.1rem 0 0.4rem 0;
    }

    .stApp .ai-box p {
        margin: 0 0 0.75rem 0;
    }

    .stApp .ai-box ul,
    .stApp .ai-box ol {
        margin: 0.2rem 0 0.8rem 0;
        padding-left: 1.3rem;
    }

    .stApp .ai-box li {
        margin-bottom: 0.3rem;
    }

    .stApp .chips {
        display: flex;
        gap: 0.7rem;
        flex-wrap: wrap;
        margin: 0.2rem 0 0.9rem 0;
    }

    .stApp .chip {
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-radius: 10px;
        padding: 0.45rem 0.8rem;
        font-size: 0.85rem;
    }

    .stApp .chip b {
        color: #4C1D95;
    }

    /* ---------- Footer ---------- */

    .stApp .app-footer {
        margin-top: 4rem;
        padding-top: 1.5rem;
        border-top: 1px solid #E6DCFB;
        text-align: center;
        color: #6B6784;
        font-size: 0.82rem;
        line-height: 1.8;
    }
    </style>
    """
)


# ============================================================
# API CONNECTION CHECK
# ============================================================

try:
    summary_data = get_summary()

except Exception as error:
    st.error(
        "PayResolve API is not running. "
        "Start FastAPI first with: "
        "`uvicorn api.main:app --reload`"
    )
    st.exception(error)
    st.stop()


# ============================================================
# HERO
# ============================================================

render_html(
    """
    <div class="hero">
        <div>
            <div class="hero-title">PayResolve</div>
            <p class="hero-sub">
                Investigate payment failures, reconciliation exceptions,
                anomalies and operational incidents using structured
                payment evidence and AI-assisted investigation.
            </p>
        </div>
        <div class="hero-pill">API connected</div>
    </div>
    """
)


# ============================================================
# SIDEBAR
# ============================================================

render_html(
    """
    <div class="brand">PayResolve</div>
    <div class="brand-sub">Payment Operations Intelligence Platform</div>
    """,
    st.sidebar,
)

st.sidebar.divider()

st.sidebar.caption(
    "Filters apply to the payment status charts and "
    "the transaction investigation section."
)

all_transactions = get_transactions(limit=500)

transactions_df = pd.DataFrame(all_transactions.get("transactions", []))

if transactions_df.empty:
    st.warning("No transaction data available.")
    st.stop()

selected_status = st.sidebar.selectbox(
    "Payment status",
    ["All"] + unique_values(transactions_df, "status"),
)

selected_provider = st.sidebar.selectbox(
    "Provider",
    ["All"] + unique_values(transactions_df, "provider"),
)

selected_incident = st.sidebar.selectbox(
    "Incident type",
    ["All"] + unique_values(transactions_df, "incident_type"),
)

if st.sidebar.button("Refresh data", width="stretch"):
    st.cache_data.clear()
    st.rerun()


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_response = get_transactions(
    status=None if selected_status == "All" else selected_status,
    provider=None if selected_provider == "All" else selected_provider,
    incident_type=None if selected_incident == "All" else selected_incident,
    limit=500,
)

filtered_transactions = pd.DataFrame(
    filtered_response.get("transactions", [])
)


# ============================================================
# OVERVIEW
# ============================================================

section(
    "Overview",
    "A high-level view of the payment operations environment.",
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    kpi_card(
        "Total transactions",
        f"{summary_data.get('total_transactions', 0):,}",
    )

with col2:
    kpi_card(
        "Success rate",
        f"{summary_data.get('success_rate', 0):.2f}%",
    )

with col3:
    kpi_card(
        "Reconciliation exceptions",
        f"{summary_data.get('reconciliation_exceptions', 0):,}",
    )

with col4:
    kpi_card(
        "Detected anomalies",
        f"{summary_data.get('detected_anomalies', 0):,}",
    )


# ============================================================
# PAYMENT STATUS
# ============================================================

section(
    "Payment status",
    "Distribution of transactions across final payment states.",
)

if not filtered_transactions.empty:
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            chart_title("Transactions by status")

            status_chart = (
                filtered_transactions.groupby("status")
                .size()
                .reset_index(name="count")
            )

            bar_chart(
                status_chart,
                "status",
                order=rank_order(
                    status_chart["status"].tolist(),
                    STATUS_ORDER,
                ),
            )

    with col2:
        with st.container(border=True):
            chart_title("Transactions by provider")

            provider_chart = (
                filtered_transactions.groupby("provider")
                .size()
                .reset_index(name="count")
            )

            bar_chart(provider_chart, "provider")

else:
    st.info("No transactions match the current filters.")


# ============================================================
# INCIDENT ANALYSIS
# ============================================================

section(
    "Incident analysis",
    "Classification of payment incidents and operational priorities.",
)

incident_df = pd.DataFrame(
    get_incidents(limit=500).get("incidents", [])
)

if not incident_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            chart_title("Incident types")

            incident_chart = (
                incident_df.groupby("incident_type")
                .size()
                .reset_index(name="count")
            )

            bar_chart(
                incident_chart,
                "incident_type",
                horizontal=True,
                height=350,
            )

    with col2:
        with st.container(border=True):
            chart_title(
                "Investigation priorities",
                "Darker bars are higher priority",
            )

            priority_chart = (
                incident_df.groupby("priority")
                .size()
                .reset_index(name="count")
            )

            bar_chart(
                priority_chart,
                "priority",
                order=rank_order(
                    priority_chart["priority"].tolist(),
                    PRIORITY_ORDER,
                ),
                severity=True,
                height=350,
            )

else:
    st.info("No incidents found.")


# ============================================================
# ANOMALY DETECTION
# ============================================================

section(
    "Anomaly detection",
    "Machine-learning signals used to surface unusual payment records.",
)

anomaly_df = pd.DataFrame(
    get_anomalies(limit=500).get("anomalies", [])
)

if not anomaly_df.empty:
    with st.container(border=True):
        chart_title("Anomaly levels", "Darker bars are higher risk")

        anomaly_chart = (
            anomaly_df.groupby("anomaly_level")
            .size()
            .reset_index(name="count")
        )

        bar_chart(
            anomaly_chart,
            "anomaly_level",
            order=rank_order(
                anomaly_chart["anomaly_level"].tolist(),
                LEVEL_ORDER,
            ),
            severity=True,
            height=260,
        )

    subsection("Highest-risk transactions")

    highest_risk = anomaly_df.copy()

    if "anomaly_score" in highest_risk.columns:
        highest_risk = highest_risk.sort_values(
            "anomaly_score",
            ascending=False,
        )

    highest_risk = highest_risk.head(10)

    display_columns = [
        "transaction_id",
        "provider",
        "status",
        "incident_type",
        "anomaly_score",
        "anomaly_level",
    ]

    st.dataframe(
        highest_risk[
            [c for c in display_columns if c in highest_risk.columns]
        ],
        width="stretch",
        hide_index=True,
    )

else:
    st.info("No anomalies detected.")


# ============================================================
# TRANSACTION INVESTIGATION
# ============================================================

DETAIL_COLUMNS = [
    "transaction_id",
    "customer_id",
    "merchant_id",
    "merchant_category",
    "provider",
    "bank",
    "payment_method",
    "currency",
    "amount",
    "created_at",
    "status",
    "reconciliation_status",
    "incident_type",
    "incident_category",
    "priority",
    "recommended_owner",
    "recommended_action",
    "anomaly_prediction",
    "anomaly_score",
    "anomaly_level",
    "potential_duplicate",
]

WIDE_DETAILS = {"recommended_action"}


def render_details(transaction):
    cells = "".join(
        f"""
        <div class="detail{' detail-wide' if key in WIDE_DETAILS else ''}">
            <div class="detail-label">{escape(key.replace("_", " ").capitalize())}</div>
            <div class="detail-value">{escape(format_value(key, transaction.get(key)))}</div>
        </div>
        """
        for key in DETAIL_COLUMNS
        if key in transaction
    )

    render_html(f'<div class="detail-grid">{cells}</div>')


def render_timeline(records):
    items = "".join(
        f"""
        <div class="tl-item">
            <div class="tl-top">
                <div class="tl-event">{escape(text_or(event.get("event_type"), "UNKNOWN"))}</div>
                {status_badge(event.get("event_status"))}
            </div>
            <div class="tl-meta">
                <span>Provider: {escape(text_or(event.get("provider"), "UNKNOWN"))}</span>
                <span>{escape(text_or(event.get("event_timestamp"), "UNKNOWN"))}</span>
            </div>
        </div>
        """
        for event in records
    )

    render_html(f'<div class="timeline">{items}</div>')


def render_transaction_investigation(selected_transaction):
    try:
        transaction = get_transaction(selected_transaction)

    except Exception as error:
        st.error(
            f"Unable to load transaction {selected_transaction}: {error}"
        )
        return

    incident_type = transaction.get("incident_type", "NONE")
    anomaly_level = transaction.get("anomaly_level", "LOW")
    anomaly_score = transaction.get("anomaly_score", 0)
    reconciliation = transaction.get("reconciliation_status")

    # --------------------------------------------------------
    # Header and KPI row
    # --------------------------------------------------------

    recon_note = (
        f'<span class="txn-note">Reconciliation: {escape(str(reconciliation))}</span>'
        if reconciliation
        else ""
    )

    render_html(
        f"""
        <div class="txn-head">
            <span class="txn-id">{escape(str(selected_transaction))}</span>
            {status_badge(transaction.get("status"))}
            {recon_note}
        </div>
        """
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        kpi_card(
            "Status",
            status_badge(transaction.get("status", "UNKNOWN")),
            small=True,
        )

    with col2:
        kpi_card("Amount", naira(transaction.get("amount", 0)))

    with col3:
        kpi_card("Incident", escape(str(incident_type)), small=True)

    with col4:
        kpi_card("Anomaly level", escape(str(anomaly_level)), small=True)

    # --------------------------------------------------------
    # Transaction details
    # --------------------------------------------------------

    subsection("Transaction details")

    render_details(transaction)

    # --------------------------------------------------------
    # Payment timeline
    # --------------------------------------------------------

    subsection("Payment timeline")

    try:
        timeline_records = get_transaction_timeline(
            selected_transaction
        ).get("timeline", [])

        if timeline_records:
            render_timeline(timeline_records)

        else:
            st.info(
                "No payment events were recorded for this transaction."
            )

    except Exception as error:
        st.warning(f"Unable to load payment timeline: {error}")

    # --------------------------------------------------------
    # On-demand AI investigation
    # --------------------------------------------------------

    subsection("AI investigation")

    render_html(
        """
        <div class="gen-card">
            <strong>Evidence-first investigation</strong>
            <p>
                Generate an AI-assisted investigation using the
                transaction record, payment events, reconciliation
                results, incident classification and anomaly signals.
            </p>
            <p class="muted">
                The AI does not make payment decisions or invent
                missing evidence. Unknown information is explicitly
                identified for human investigation.
            </p>
        </div>
        """
    )

    if st.button(
        "Generate AI investigation",
        key=f"generate_ai_{selected_transaction}",
        width="stretch",
    ):
        with st.spinner("Generating evidence-based AI investigation..."):
            try:
                result = generate_ai_investigation(selected_transaction)

                # Clear cached transaction data so the newly
                # saved AI investigation is loaded.
                get_transaction.clear()

                st.session_state[
                    f"ai_generated_{selected_transaction}"
                ] = result.get("ai_explanation", "")

                st.success("AI investigation generated and saved.")

            except requests.exceptions.HTTPError as error:
                try:
                    error_detail = error.response.json().get(
                        "detail",
                        str(error),
                    )
                except Exception:
                    error_detail = str(error)

                st.error(f"AI investigation failed: {error_detail}")

            except Exception as error:
                st.error(f"AI investigation failed: {error}")

    # Show the latest AI investigation (freshly generated or stored)

    ai_explanation = st.session_state.get(
        f"ai_generated_{selected_transaction}"
    ) or transaction.get("ai_explanation")

    if ai_explanation:
        render_html(
            f"""
            <div class="ai-box">
                <div class="ai-title">Evidence-based AI investigation</div>
                {format_text(ai_explanation)}
            </div>
            """
        )

    else:
        render_html(
            f"""
            <div class="ai-box">
                <div class="ai-title">Investigation not generated yet</div>
                <div class="chips">
                    <div class="chip">Incident: <b>{escape(str(incident_type))}</b></div>
                    <div class="chip">Anomaly level: <b>{escape(str(anomaly_level))}</b></div>
                    <div class="chip">Anomaly score: <b>{escape(format_value("anomaly_score", anomaly_score))}</b></div>
                </div>
                Click <strong>Generate AI investigation</strong> above
                to investigate this transaction.
            </div>
            """
        )


section(
    "Transaction investigation",
    "Inspect a specific payment and its recorded lifecycle.",
)

transaction_ids = (
    filtered_transactions["transaction_id"].dropna().astype(str).tolist()
    if "transaction_id" in filtered_transactions.columns
    else []
)

if transaction_ids:
    chosen_transaction = st.selectbox(
        "Select a transaction",
        transaction_ids,
        key="selected_transaction",
    )

    render_transaction_investigation(chosen_transaction)

else:
    st.info("No transactions match the current filters.")


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
    <div class="app-footer">
        PayResolve is an experimental payment operations intelligence platform.
        <br>
        Synthetic data only. No real financial transactions.
    </div>
    """
)