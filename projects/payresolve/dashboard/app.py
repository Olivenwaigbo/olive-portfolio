from pathlib import Path
import json
import os
import sys
import re
from html import escape

import altair as alt
import pandas as pd
import requests
import streamlit as st


# ============================================================
# STREAMLIT CONFIG
# ============================================================

st.set_page_config(
    page_title="PayResolve",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# ============================================================
# GROQ / STREAMLIT CLOUD SECRET
# ============================================================

# Locally, src/ai_explainer.py can read the GROQ_API_KEY
# from .env.
#
# On Streamlit Community Cloud, the key will normally be
# stored in Streamlit Secrets. We copy it into the environment
# so the existing AI module can use it without changing the
# product architecture.

try:
    groq_secret = st.secrets["GROQ_API_KEY"]

    if groq_secret:
        os.environ["GROQ_API_KEY"] = groq_secret

except Exception:
    pass


from src.ai_explainer import investigate_transaction


# Follow-up questions call Groq's OpenAI-compatible endpoint directly.
# Set GROQ_MODEL (environment variable or Streamlit secret) to change
# the model without editing this file.

def _secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return None


GROQ_MODEL = (
    os.environ.get("GROQ_MODEL")
    or _secret("GROQ_MODEL")
    or "openai/gpt-oss-20b"
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


# ============================================================
# COLOURS (white and purple)
# ============================================================

PURPLE = "#7C3AED"
DEEP_PURPLE = "#4C1D95"
MUTED = "#6B6784"

# Darkest purple = most severe
SEVERITY_RAMP = ["#4C1D95", "#6D28D9", "#8B5CF6", "#C4B5FD", "#DDD6FE"]

STATUS_ORDER = ["SUCCESS", "FAILED", "PENDING", "REVERSED"]
PRIORITY_ORDER = ["P1", "P2", "P3", "P4", "NONE"]
LEVEL_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]

YES_NO_KEYS = {
    "potential_duplicate",
    "has_success",
    "has_settlement",
    "has_reversal",
    "has_failure",
    "has_pending",
    "has_timeout",
    "has_debit",
}

WIDE_DETAILS = {"recommended_action"}


# ============================================================
# HTML HELPERS
# ============================================================
# Streamlit runs st.markdown() through a Markdown parser first.
# Markdown treats any line indented by 4+ spaces as a code block,
# and a blank line ends an HTML block. That is why indented HTML
# was printed as raw text. render_html() strips the indentation and
# blank lines so each snippet is treated as one HTML block.


def render_html(markup: str):
    cleaned = "\n".join(
        line.strip()
        for line in markup.strip().splitlines()
        if line.strip()
    )
    st.markdown(cleaned, unsafe_allow_html=True)


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

    .stApp .brand {
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #4C1D95;
    }

    .stApp .brand-sub {
        color: #6B6784;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-top: 0.3rem;
    }

    .stApp .side-heading {
        font-size: 1rem;
        font-weight: 700;
        color: #1E1B2E;
        margin-bottom: 0.2rem;
    }

    .stApp .side-note-title {
        font-size: 0.85rem;
        font-weight: 700;
        color: #4C1D95;
        margin-bottom: 0.4rem;
    }

    .stApp .side-note {
        font-size: 0.85rem;
        color: #6B6784;
        line-height: 1.9;
    }

    /* ---------- Buttons and inputs ---------- */

    .stApp .stButton > button {
        background-color: #7C3AED;
        border: 1px solid #7C3AED;
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
        border-color: #6D28D9;
    }

    .stApp .stButton > button[data-testid="stBaseButton-secondary"] {
        background-color: #ffffff;
        border: 1px solid #C4B5FD;
    }

    .stApp .stButton > button[data-testid="stBaseButton-secondary"] p {
        color: #5B21B6;
    }

    .stApp .stButton > button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #F5F0FF;
        border-color: #7C3AED;
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

    /* ---------- Header ---------- */

    .stApp .hero {
        padding: 0.4rem 0 1.6rem 0;
        margin-bottom: 0.4rem;
        border-bottom: 1px solid #E6DCFB;
    }

    .stApp .hero-title {
        color: #7C3AED;
        font-size: 4.4rem;
        font-weight: 800;
        letter-spacing: -0.045em;
        line-height: 1.02;
    }

    .stApp .hero-sub {
        color: #1E1B2E;
        font-size: 1.15rem;
        line-height: 1.6;
        max-width: 46rem;
        margin: 0.8rem 0 0 0;
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
    /* Every card in a row reserves the same space (two label lines,
       one value line, two note lines) so the rows always line up. */

    .stApp .kpi-card {
        box-sizing: border-box;
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-left: 4px solid #7C3AED;
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        min-height: 9.8rem;
    }

    .stApp .kpi-card-compact {
        min-height: 6.6rem;
    }

    .stApp .kpi-label {
        color: #6B6784;
        font-size: 0.85rem;
        font-weight: 500;
        line-height: 1.25;
        min-height: 2.13rem;
        margin-bottom: 0.45rem;
    }

    .stApp .kpi-card-compact .kpi-label {
        min-height: 0;
        margin-bottom: 0.6rem;
    }

    .stApp .kpi-value {
        color: #4C1D95;
        font-size: clamp(1.45rem, 1.7vw, 1.9rem);
        font-weight: 800;
        letter-spacing: -0.02em;
        line-height: 1.2;
        white-space: nowrap;
    }

    .stApp .kpi-value-md {
        font-size: clamp(1.15rem, 1.4vw, 1.5rem);
    }

    .stApp .kpi-value-sm {
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: 0;
        line-height: 1.4;
        white-space: normal;
        word-break: break-word;
    }

    .stApp .kpi-note {
        color: #8A85A0;
        font-size: 0.78rem;
        line-height: 1.35;
        min-height: 2.1rem;
        margin-top: 0.45rem;
    }

    /* ---------- Badges ---------- */

    .stApp .badge {
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

    /* ---------- Evidence grid ---------- */

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

    /* ---------- Follow-up questions ---------- */

    .stApp .ask-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1E1B2E;
        margin: 1.6rem 0 0.2rem 0;
    }

    .stApp .ask-sub {
        color: #6B6784;
        font-size: 0.88rem;
        margin-bottom: 0.7rem;
    }

    .stApp [data-testid="stForm"] {
        border: 1px solid #E6DCFB;
        border-radius: 14px;
        background: #FAF7FF;
        padding: 0.9rem 1rem;
    }

    .stApp [data-baseweb="input"],
    .stApp [data-baseweb="base-input"] {
        border-radius: 10px;
        border-color: #E6DCFB;
        background-color: #ffffff;
    }

    .stApp [data-baseweb="base-input"] input {
        background-color: #ffffff;
    }

    .stApp [data-baseweb="input"]:focus-within {
        border-color: #7C3AED;
        box-shadow: 0 0 0 1px #7C3AED;
    }

    .stApp [data-testid="stFormSubmitButton"] > button {
        background-color: #7C3AED;
        border: 1px solid #7C3AED;
        border-radius: 10px;
        font-weight: 600;
        min-height: 42px;
    }

    .stApp [data-testid="stFormSubmitButton"] > button p {
        color: #ffffff;
    }

    .stApp [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #6D28D9;
        border-color: #6D28D9;
    }

    .stApp .qa-card {
        background: #ffffff;
        border: 1px solid #E6DCFB;
        border-radius: 14px;
        padding: 1rem 1.3rem;
        margin-top: 0.8rem;
    }

    .stApp .qa-q {
        font-weight: 700;
        color: #4C1D95;
        margin-bottom: 0.5rem;
    }

    .stApp .qa-a {
        color: #1E1B2E;
        line-height: 1.7;
    }

    .stApp .qa-a p {
        margin: 0 0 0.6rem 0;
    }

    .stApp .qa-a ul,
    .stApp .qa-a ol {
        margin: 0.2rem 0 0.7rem 0;
        padding-left: 1.3rem;
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
# DISPLAY HELPERS
# ============================================================


def format_text(value) -> str:
    """
    Turn AI output (light Markdown) into safe HTML.
    Supports **bold**, headings, bullet lists and numbered lists.
    All text is escaped first, so it cannot inject HTML.
    """

    if value is None:
        return "—"

    if isinstance(value, float) and pd.isna(value):
        return "—"

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


def text_or(value, fallback="—"):
    if value is None:
        return fallback

    if isinstance(value, float) and pd.isna(value):
        return fallback

    if pd.isna(value):
        return fallback

    value = str(value).strip()

    return value if value else fallback


def naira(value):
    try:
        return f"₦{float(value):,.2f}"
    except Exception:
        return "—"


def status_badge(status):
    status = text_or(status, "UNKNOWN").upper()

    classes = {
        "SUCCESS": "badge-success",
        "FAILED": "badge-failed",
        "PENDING": "badge-pending",
        "REVERSED": "badge-reversed",
    }

    css_class = classes.get(status, "badge-default")

    return f'<span class="badge {css_class}">{escape(status)}</span>'


def format_value(key, value):
    """Return an HTML-safe string for one evidence field."""

    if key == "status":
        return status_badge(value)

    display = text_or(value)

    if display == "—":
        return "—"

    if key == "amount":
        return naira(value)

    if key in YES_NO_KEYS:
        return "Yes" if display.lower() in {"true", "1", "1.0", "yes"} else "No"

    if key == "anomaly_score":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return escape(display)

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.2f}"

    return escape(display)


def section(title, subtitle=None):
    subtitle_html = (
        f'<div class="section-sub">{escape(subtitle)}</div>'
        if subtitle
        else ""
    )

    render_html(
        f"""
        <div class="section">
            <div class="section-title">{escape(title)}</div>
            {subtitle_html}
        </div>
        """
    )


def subsection(title):
    render_html(f'<div class="sub-title">{escape(title)}</div>')


def chart_title(title, subtitle=None):
    subtitle_html = (
        f'<div class="chart-sub">{escape(subtitle)}</div>'
        if subtitle
        else ""
    )

    render_html(
        f"""
        <div class="chart-title">{escape(title)}</div>
        {subtitle_html}
        """
    )


def kpi_card(label, value, note="", html=False, size="lg"):
    """
    Render a KPI card.
    size: "lg" (big number), "md" (amounts), "sm" (text that may wrap).
    If html=True, value must already be safe HTML (e.g. a badge).
    Cards without a note use a shorter, compact layout.
    """

    value_html = value if html else escape(str(value))
    size_class = {"lg": "", "md": " kpi-value-md", "sm": " kpi-value-sm"}[size]
    card_class = "kpi-card" if note else "kpi-card kpi-card-compact"
    note_html = f'<div class="kpi-note">{escape(note)}</div>' if note else ""

    render_html(
        f"""
        <div class="{card_class}">
            <div class="kpi-label">{escape(label)}</div>
            <div class="kpi-value{size_class}">{value_html}</div>
            {note_html}
        </div>
        """
    )


def count_table(series):
    return (
        series
        .value_counts()
        .rename_axis("label")
        .reset_index(name="count")
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

    values = (
        df[column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return sorted(values)


def bar_chart(
    df,
    category="label",
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
# DATA LOADING
# ============================================================

def required_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required data file not found: {path}"
        )


@st.cache_data(ttl=60)
def load_payresolve_data():
    """
    Load the final PayResolve analytical datasets.

    The anomaly dataset is the main transaction table because
    it is downstream of reconciliation and incident
    classification.

    Missing columns are recovered from earlier pipeline files
    when necessary.
    """

    transactions_path = DATA_DIR / "transactions_test.csv"
    reconciliation_path = DATA_DIR / "reconciliation_test_results.csv"
    incident_path = DATA_DIR / "incident_classification_results.csv"
    anomaly_path = DATA_DIR / "anomaly_detection_results.csv"
    events_path = DATA_DIR / "events_test.csv"
    ai_path = DATA_DIR / "ai_explanations.csv"

    for path in [
        transactions_path,
        reconciliation_path,
        incident_path,
        anomaly_path,
        events_path,
    ]:
        required_file(path)

    transactions = pd.read_csv(transactions_path)
    reconciliation = pd.read_csv(reconciliation_path)
    incidents = pd.read_csv(incident_path)
    anomalies = pd.read_csv(anomaly_path)
    events = pd.read_csv(events_path)

    # The anomaly dataset should already contain most fields.
    df = anomalies.copy()

    # Recover any missing fields from upstream datasets.
    upstream_sources = [
        incidents,
        reconciliation,
        transactions,
    ]

    for source in upstream_sources:
        if "transaction_id" not in source.columns:
            continue

        source = source.loc[
            :,
            ~source.columns.duplicated()
        ].copy()

        missing_columns = [
            column
            for column in source.columns
            if column not in df.columns
            and column != "transaction_id"
        ]

        if missing_columns:
            merge_columns = [
                "transaction_id"
            ] + missing_columns

            df = df.merge(
                source[merge_columns],
                on="transaction_id",
                how="left",
            )

    # AI explanations are optional.
    # They are generated as the user investigates transactions.
    if ai_path.exists():
        ai = pd.read_csv(ai_path)

        if "transaction_id" in ai.columns:

            ai_column = None

            for candidate in [
                "ai_explanation",
                "explanation",
            ]:
                if candidate in ai.columns:
                    ai_column = candidate
                    break

            if ai_column:
                ai = ai[
                    [
                        "transaction_id",
                        ai_column,
                    ]
                ].drop_duplicates(
                    "transaction_id",
                    keep="last",
                )

                if ai_column != "ai_explanation":
                    ai = ai.rename(
                        columns={
                            ai_column: "ai_explanation"
                        }
                    )

                if "ai_explanation" not in df.columns:
                    df = df.merge(
                        ai,
                        on="transaction_id",
                        how="left",
                    )

    if "transaction_id" in df.columns:
        df["transaction_id"] = (
            df["transaction_id"]
            .astype(str)
        )

    if "transaction_id" in events.columns:
        events["transaction_id"] = (
            events["transaction_id"]
            .astype(str)
        )

    return df, events


# ============================================================
# DATA HELPERS
# ============================================================

def anomaly_mask(df):
    """
    Isolation Forest normally returns:
        -1 = anomaly
         1 = normal

    This helper also supports text-based anomaly labels.
    """

    if "anomaly_prediction" not in df.columns:
        return pd.Series(
            False,
            index=df.index,
        )

    numeric = pd.to_numeric(
        df["anomaly_prediction"],
        errors="coerce",
    )

    if numeric.notna().any():
        return numeric == -1

    normalized = (
        df["anomaly_prediction"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    return normalized.isin(
        [
            "ANOMALY",
            "OUTLIER",
            "TRUE",
        ]
    )


def get_summary(df):
    total = len(df)

    if total == 0:
        return {
            "total_transactions": 0,
            "success_rate": 0,
            "reconciliation_exceptions": 0,
            "detected_anomalies": 0,
        }

    success_rate = 0

    if "status" in df.columns:
        success_rate = (
            df["status"]
            .astype(str)
            .str.upper()
            .eq("SUCCESS")
            .mean()
            * 100
        )

    if "reconciliation_status" in df.columns:
        exceptions = (
            df["reconciliation_status"]
            .astype(str)
            .str.upper()
            .eq("EXCEPTION")
            .sum()
        )

    elif "incident_type" in df.columns:
        exceptions = (
            df["incident_type"]
            .astype(str)
            .str.upper()
            .ne("NONE")
            .sum()
        )

    else:
        exceptions = 0

    anomalies = int(
        anomaly_mask(df).sum()
    )

    return {
        "total_transactions": total,
        "success_rate": success_rate,
        "reconciliation_exceptions": exceptions,
        "detected_anomalies": anomalies,
    }


def get_filtered_transactions(
    df,
    status="All",
    provider="All",
    incident_type="All",
):
    result = df.copy()

    if status != "All" and "status" in result.columns:
        result = result[
            result["status"]
            .astype(str)
            .eq(status)
        ]

    if provider != "All" and "provider" in result.columns:
        result = result[
            result["provider"]
            .astype(str)
            .eq(provider)
        ]

    if (
        incident_type != "All"
        and "incident_type" in result.columns
    ):
        result = result[
            result["incident_type"]
            .astype(str)
            .eq(incident_type)
        ]

    return result


def get_incidents_df(
    df,
    priority="All",
    incident_type="All",
):
    result = df.copy()

    if "incident_type" in result.columns:
        result = result[
            result["incident_type"]
            .astype(str)
            .str.upper()
            .ne("NONE")
        ]

    if priority != "All" and "priority" in result.columns:
        result = result[
            result["priority"]
            .astype(str)
            .eq(priority)
        ]

    if (
        incident_type != "All"
        and "incident_type" in result.columns
    ):
        result = result[
            result["incident_type"]
            .astype(str)
            .eq(incident_type)
        ]

    return result


def get_anomalies_df(df, level="All"):
    result = df.loc[
        anomaly_mask(df)
    ].copy()

    if level != "All" and "anomaly_level" in result.columns:
        result = result[
            result["anomaly_level"]
            .astype(str)
            .eq(level)
        ]

    if "anomaly_score" in result.columns:
        result["anomaly_score"] = pd.to_numeric(
            result["anomaly_score"],
            errors="coerce",
        )

        result = result.sort_values(
            "anomaly_score",
            ascending=False,
        )

    return result


def get_transaction(df, transaction_id):
    matches = df[
        df["transaction_id"]
        .astype(str)
        .eq(str(transaction_id))
    ]

    if matches.empty:
        return None

    return matches.iloc[0]


def get_transaction_timeline(events, transaction_id):
    result = events[
        events["transaction_id"]
        .astype(str)
        .eq(str(transaction_id))
    ].copy()

    if result.empty:
        return result

    if "event_timestamp" in result.columns:
        result["event_timestamp"] = pd.to_datetime(
            result["event_timestamp"],
            errors="coerce",
        )

        result = result.sort_values(
            "event_timestamp"
        )

    return result


# ============================================================
# LOAD DATA
# ============================================================

try:
    df, events_df = load_payresolve_data()

except FileNotFoundError as error:
    st.error(str(error))
    st.info(
        "Make sure you have generated the PayResolve datasets "
        "and pushed the data/ folder to GitHub."
    )
    st.stop()

except Exception as error:
    st.error(
        f"PayResolve could not load its data: {error}"
    )
    st.stop()


# ============================================================
# HERO
# ============================================================

render_html(
    """
    <div class="hero">
        <div class="hero-title">PayResolve</div>
        <p class="hero-sub">
            An experimental payment operations intelligence platform
            for investigating transaction failures, anomalies and
            reconciliation exceptions.
        </p>
    </div>
    """
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    render_html(
        """
        <div class="brand">PayResolve</div>
        <div class="brand-sub">Payment Operations Intelligence</div>
        """
    )

    st.divider()

    render_html('<div class="side-heading">Filters</div>')

    st.caption(
        "Filters narrow the transaction list in the "
        "Transaction investigation section."
    )

    selected_status = st.selectbox(
        "Payment status",
        ["All"] + unique_values(df, "status"),
    )

    selected_provider = st.selectbox(
        "Provider",
        ["All"] + unique_values(df, "provider"),
    )

    selected_incident = st.selectbox(
        "Incident type",
        ["All"] + unique_values(df, "incident_type"),
    )

    if st.button(
        "↻ Refresh data",
        width="stretch",
    ):
        st.cache_data.clear()
        st.rerun()

    st.divider()

    render_html(
        """
        <div class="side-note-title">Prototype principles</div>
        <div class="side-note">
            Evidence first<br>
            Human in the loop<br>
            Traceable investigations<br>
            Synthetic data only
        </div>
        """
    )


# ============================================================
# SUMMARY
# ============================================================

summary = get_summary(df)

section(
    "Operations overview",
    "A high-level view of the synthetic payment environment.",
)

kpi_columns = st.columns(4)

with kpi_columns[0]:
    kpi_card(
        "Total transactions",
        f"{summary['total_transactions']:,}",
        "Synthetic payment records",
    )

with kpi_columns[1]:
    kpi_card(
        "Success rate",
        f"{summary['success_rate']:.1f}%",
        "Transactions with SUCCESS status",
    )

with kpi_columns[2]:
    kpi_card(
        "Reconciliation exceptions",
        f"{summary['reconciliation_exceptions']:,}",
        "Records requiring investigation",
    )

with kpi_columns[3]:
    kpi_card(
        "Detected anomalies",
        f"{summary['detected_anomalies']:,}",
        "Isolation Forest outliers",
    )


# ============================================================
# PAYMENT STATUS
# ============================================================

section(
    "Payment status",
    "Understand transaction outcomes across the generated dataset.",
)

chart_columns = st.columns(2)

with chart_columns[0]:
    with st.container(border=True):
        chart_title("Transaction status")

        if "status" in df.columns:
            status_data = count_table(df["status"].astype(str))

            bar_chart(
                status_data,
                order=rank_order(
                    status_data["label"].tolist(),
                    STATUS_ORDER,
                ),
            )

with chart_columns[1]:
    with st.container(border=True):
        chart_title("Provider distribution")

        if "provider" in df.columns:
            provider_data = count_table(df["provider"].astype(str))

            bar_chart(provider_data)


# ============================================================
# INCIDENT ANALYSIS
# ============================================================

section(
    "Incident analysis",
    "Reconciliation rules and operational classification.",
)

incident_df = get_incidents_df(df)

chart_columns = st.columns(2)

with chart_columns[0]:
    with st.container(border=True):
        chart_title("Incident types")

        if (
            not incident_df.empty
            and "incident_type" in incident_df.columns
        ):
            incident_data = count_table(
                incident_df["incident_type"].astype(str)
            )

            bar_chart(
                incident_data,
                horizontal=True,
                height=350,
            )

        else:
            st.info("No incidents found.")

with chart_columns[1]:
    with st.container(border=True):
        chart_title(
            "Investigation priorities",
            "Darker bars are higher priority",
        )

        if (
            not incident_df.empty
            and "priority" in incident_df.columns
        ):
            priority_data = count_table(
                incident_df["priority"].astype(str)
            )

            bar_chart(
                priority_data,
                order=rank_order(
                    priority_data["label"].tolist(),
                    PRIORITY_ORDER,
                ),
                severity=True,
                height=350,
            )

        else:
            st.info("No priority data found.")


# ============================================================
# ANOMALY DETECTION
# ============================================================

section(
    "Anomaly detection",
    "Machine-learning signals that help prioritize unusual transactions.",
)

anomalies_df = get_anomalies_df(df)

anomaly_columns = st.columns(2)

with anomaly_columns[0]:
    with st.container(border=True):
        chart_title(
            "Detected anomaly levels",
            "Darker bars are higher risk",
        )

        if (
            not anomalies_df.empty
            and "anomaly_level" in anomalies_df.columns
        ):
            level_data = count_table(
                anomalies_df["anomaly_level"].astype(str)
            )

            bar_chart(
                level_data,
                order=rank_order(
                    level_data["label"].tolist(),
                    LEVEL_ORDER,
                ),
                severity=True,
                height=340,
            )

        else:
            st.info("No anomalies detected.")

with anomaly_columns[1]:
    with st.container(border=True):
        chart_title("Highest-risk transactions")

        if not anomalies_df.empty:

            display_columns = [
                column
                for column in [
                    "transaction_id",
                    "provider",
                    "status",
                    "incident_type",
                    "anomaly_score",
                    "anomaly_level",
                ]
                if column in anomalies_df.columns
            ]

            display_df = anomalies_df[
                display_columns
            ].head(10).copy()

            if "anomaly_score" in display_df.columns:
                display_df["anomaly_score"] = (
                    pd.to_numeric(
                        display_df["anomaly_score"],
                        errors="coerce",
                    )
                    .round(2)
                )

            st.dataframe(
                display_df,
                width="stretch",
                hide_index=True,
            )

        else:
            st.info("No anomalies detected.")


# ============================================================
# TRANSACTION INVESTIGATION
# ============================================================

EVIDENCE_COLUMNS = [
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


def render_evidence(transaction):
    cells = "".join(
        f"""
        <div class="detail{' detail-wide' if column in WIDE_DETAILS else ''}">
            <div class="detail-label">{escape(column.replace("_", " ").capitalize())}</div>
            <div class="detail-value">{format_value(column, transaction[column])}</div>
        </div>
        """
        for column in EVIDENCE_COLUMNS
        if column in transaction.index
    )

    render_html(f'<div class="detail-grid">{cells}</div>')


def render_timeline(timeline_df):
    items = "".join(
        f"""
        <div class="tl-item">
            <div class="tl-top">
                <div class="tl-event">{escape(text_or(event.get("event_type")))}</div>
                {status_badge(event.get("event_status"))}
            </div>
            <div class="tl-meta">
                <span>Provider: {escape(text_or(event.get("provider")))}</span>
                <span>{escape(text_or(event.get("event_timestamp")))}</span>
            </div>
        </div>
        """
        for _, event in timeline_df.iterrows()
    )

    render_html(f'<div class="timeline">{items}</div>')


FOLLOWUP_SYSTEM_PROMPT = """You are the PayResolve investigation assistant. You help a payment operations analyst understand one transaction.

Rules:
- Answer only from the evidence supplied below: the transaction record, the payment event timeline and any earlier AI investigation.
- If the evidence does not answer the question, say what is unknown and what the analyst should check next. Never invent events, amounts, timestamps or causes.
- You do not approve, reverse, refund or otherwise decide on payments. Recommend the responsible team or next step and leave the decision to a human.
- Keep answers short and practical, using short paragraphs or bullet points. Refer to fields by name where useful.

EVIDENCE (JSON):
"""


def ensure_groq_key():
    if os.environ.get("GROQ_API_KEY"):
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(BASE_DIR / ".env")

    except Exception:
        pass


def build_evidence_context(transaction, timeline_df, investigation_text):
    record = {
        column: (value.item() if hasattr(value, "item") else value)
        for column, value in transaction.items()
        if column != "ai_explanation" and not pd.isna(value)
    }

    events = [
        {
            "event_type": text_or(event.get("event_type")),
            "event_status": text_or(event.get("event_status")),
            "provider": text_or(event.get("provider")),
            "event_timestamp": text_or(event.get("event_timestamp")),
        }
        for _, event in timeline_df.iterrows()
    ]

    context = {
        "transaction": record,
        "payment_events": events,
    }

    if investigation_text:
        context["earlier_ai_investigation"] = str(investigation_text)

    return json.dumps(context, default=str, indent=1)


def ask_followup(
    transaction,
    timeline_df,
    investigation_text,
    history,
    question,
):
    ensure_groq_key()

    api_key = os.environ.get("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env locally "
            "or to Streamlit secrets."
        )

    evidence = build_evidence_context(
        transaction,
        timeline_df,
        investigation_text,
    )

    messages = [
        {
            "role": "system",
            "content": FOLLOWUP_SYSTEM_PROMPT + evidence,
        }
    ]

    # Keep the last few exchanges so follow-ups make sense.
    for turn in history[-6:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer"]})

    messages.append({"role": "user", "content": question})

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 700,
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            f"Groq returned {response.status_code}: {response.text[:300]}"
        )

    return response.json()["choices"][0]["message"]["content"].strip()


def render_followup(
    transaction_id,
    transaction,
    timeline_df,
    investigation_text,
):
    chat_key = f"chat_{transaction_id}"
    history = st.session_state.setdefault(chat_key, [])

    render_html(
        """
        <div class="ask-title">Ask a follow-up question</div>
        <div class="ask-sub">
            Answers come from this transaction's recorded evidence.
            The AI does not make payment decisions.
        </div>
        """
    )

    with st.form(key=f"ask_form_{transaction_id}", clear_on_submit=True):

        input_column, button_column = st.columns([6, 1])

        with input_column:
            question = st.text_input(
                "Question",
                placeholder="e.g. Why is there no settlement event?",
                label_visibility="collapsed",
            )

        with button_column:
            submitted = st.form_submit_button(
                "Ask",
                type="primary",
                width="stretch",
            )

    if submitted and question.strip():

        with st.spinner("Checking the evidence..."):

            try:
                answer = ask_followup(
                    transaction,
                    timeline_df,
                    investigation_text,
                    history,
                    question.strip(),
                )

                history.append(
                    {
                        "question": question.strip(),
                        "answer": answer,
                    }
                )

            except Exception as error:
                st.error(f"Could not get an answer: {error}")

    if history:

        if st.button(
            "Clear conversation",
            key=f"clear_chat_{transaction_id}",
        ):
            st.session_state[chat_key] = []
            st.rerun()

        # Newest answer first, directly under the search bar.
        for turn in reversed(history):
            render_html(
                f"""
                <div class="qa-card">
                    <div class="qa-q">{escape(turn["question"])}</div>
                    <div class="qa-a">{format_text(turn["answer"])}</div>
                </div>
                """
            )


section(
    "Transaction investigation",
    "Inspect a transaction, reconstruct its timeline and request an evidence-based AI investigation.",
)

filtered_df = get_filtered_transactions(
    df,
    status=selected_status,
    provider=selected_provider,
    incident_type=selected_incident,
)

if filtered_df.empty:

    st.warning(
        "No transactions match the selected filters."
    )

else:

    # Keep the selector manageable while allowing
    # the filtering logic to operate across the full dataset.
    selector_df = filtered_df.head(1000)

    transaction_ids = (
        selector_df["transaction_id"]
        .astype(str)
        .tolist()
    )

    if len(filtered_df) > len(selector_df):
        st.caption(
            f"Showing the first {len(selector_df):,} of "
            f"{len(filtered_df):,} matching transactions."
        )

    selected_transaction_id = st.selectbox(
        "Select transaction",
        transaction_ids,
    )

    transaction = get_transaction(
        df,
        selected_transaction_id,
    )

    if transaction is not None:

        detail_columns = st.columns(4)

        with detail_columns[0]:
            kpi_card(
                "Transaction",
                text_or(transaction.get("transaction_id")),
                size="sm",
            )

        with detail_columns[1]:
            kpi_card(
                "Amount",
                naira(transaction.get("amount")),
                size="md",
            )

        with detail_columns[2]:
            kpi_card(
                "Status",
                status_badge(transaction.get("status")),
                html=True,
                size="sm",
            )

        with detail_columns[3]:
            kpi_card(
                "Provider",
                text_or(transaction.get("provider")),
                size="sm",
            )

        # ---------------------------------------------
        # Transaction evidence
        # ---------------------------------------------

        subsection("Transaction evidence")

        render_evidence(transaction)

        # ---------------------------------------------
        # Timeline
        # ---------------------------------------------

        subsection("Payment timeline")

        timeline_df = get_transaction_timeline(
            events_df,
            selected_transaction_id,
        )

        if timeline_df.empty:

            st.info(
                "No recorded payment events were found "
                "for this transaction."
            )

        else:

            render_timeline(timeline_df)

        # ---------------------------------------------
        # AI Investigation
        # ---------------------------------------------

        subsection("AI investigation")

        render_html(
            """
            <div class="gen-card">
                <strong>Evidence-first AI investigation</strong>
                <p class="muted">
                    Generate an investigation using the recorded
                    transaction, reconciliation, incident,
                    anomaly and event evidence.
                </p>
            </div>
            """
        )

        ai_button = st.button(
            "Generate AI investigation",
            type="primary",
            key=f"generate_ai_{selected_transaction_id}",
            width="stretch",
        )

        if ai_button:

            with st.spinner(
                "Investigating transaction evidence..."
            ):

                try:

                    explanation = investigate_transaction(
                        selected_transaction_id
                    )

                    st.session_state[
                        f"ai_{selected_transaction_id}"
                    ] = explanation

                    # Clear cached data so a later rerun
                    # can see the saved explanation.
                    load_payresolve_data.clear()

                    st.success(
                        "AI investigation generated."
                    )

                except Exception as error:

                    st.error(
                        f"AI investigation failed: {error}"
                    )

        generated_ai = st.session_state.get(
            f"ai_{selected_transaction_id}"
        )

        stored_ai = (
            text_or(transaction.get("ai_explanation"), "")
            if "ai_explanation" in transaction.index
            else ""
        )

        if generated_ai:
            ai_title = "AI investigation"
            ai_text = generated_ai

        elif stored_ai:
            ai_title = "Stored AI investigation"
            ai_text = stored_ai

        else:
            ai_title = ""
            ai_text = ""

        if ai_text:

            render_html(
                f"""
                <div class="ai-box">
                    <div class="ai-title">{escape(ai_title)}</div>
                    {format_text(ai_text)}
                </div>
                """
            )

        render_followup(
            selected_transaction_id,
            transaction,
            timeline_df,
            ai_text,
        )


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
    <div class="app-footer">
        PayResolve is an experimental payment operations
        intelligence platform.
        <br>
        Synthetic data only. No real financial transactions.
        <br>
        AI is used for investigation support, not autonomous
        financial decision-making.
    </div>
    """
)