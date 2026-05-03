import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Weather Analytics",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CUSTOM CSS — dark industrial theme
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
    }
    .metric-card {
        background: #1a1f2e;
        border: 1px solid #2a3044;
        border-radius: 8px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 2rem;
        font-weight: 600;
        color: #4fc3f7;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #8090a0;
        margin-top: 0.3rem;
    }
    h1, h2, h3 {
        font-family: 'IBM Plex Mono', monospace;
        letter-spacing: -0.02em;
    }
    .section-header {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        color: #4fc3f7;
        border-bottom: 1px solid #2a3044;
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# API HELPERS
# ------------------------------------------------------------------
def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot reach API. Is the FastAPI server running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {e.response.status_code}: {e.response.text}")
        return None


@st.cache_data(ttl=60)
def get_cities():
    return api_get("/cities") or []


@st.cache_data(ttl=300)
def get_kpi(city):
    return api_get(f"/kpi/{city}")


@st.cache_data(ttl=300)
def get_daily_summary(city, days):
    return api_get(f"/daily-summary/{city}", {"days": days})


@st.cache_data(ttl=300)
def get_anomalies(city, limit=50):
    return api_get(f"/anomalies/{city}", {"limit": limit})


@st.cache_data(ttl=300)
def get_city_rankings():
    return api_get("/city-rankings")


@st.cache_data(ttl=300)
def get_seasonal(city):
    return api_get(f"/seasonal/{city}")


@st.cache_data(ttl=300)
def get_hourly_pattern(city):
    return api_get(f"/hourly-pattern/{city}")


# SIDEBAR
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🌤️ Weather Analytics")
    st.markdown("---")

    cities = get_cities()
    if not cities:
        st.warning("No cities found. Check API connection.")
        st.stop()

    selected_city = st.selectbox("Select City", cities)
    days = st.slider("Daily Summary Window (days)", 7, 90, 30)
    anomaly_limit = st.slider("Max anomalies to show", 10, 200, 50)

    st.markdown("---")
    health = api_get("/health")
    if health and health.get("status") == "ok":
        st.success("API ✓  DB ✓")
    else:
        st.error("API or DB unreachable")

    st.caption(f"API: `{API_BASE}`")



# MAIN CONTENT
# ------------------------------------------------------------------
st.markdown(f"# {selected_city}")
st.markdown('<div class="section-header">Key Performance Indicators (KPIs)</div>', unsafe_allow_html=True)

kpi = get_kpi(selected_city)
if kpi:
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, f"{kpi['avg_temp']} °C",   "Avg Temperature"),
        (c2, f"{kpi['avg_humidity']} %", "Avg Humidity"),
        (c3, f"{kpi['avg_wind']} km/h",  "Avg Wind Speed"),
        (c4, f"{kpi['total_precipitation']} mm", "Total Precipitation"),
        (c5, f"{kpi['record_count']:,}", "Data Points"),
    ]
    for col, val, label in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-value">{val}</div>'
                f'<div class="metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("<br>", unsafe_allow_html=True)


# DAILY SUMMARY CHART
# ------------------------------------------------------------------
st.markdown('<div class="section-header">Daily Summary</div>', unsafe_allow_html=True)

daily = get_daily_summary(selected_city, days)
if daily:
    df_daily = pd.DataFrame(daily)
    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_daily = df_daily.sort_values("date")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Avg Temperature (°C)", "Avg Humidity (%)",
                        "Total Precipitation (mm)", "Avg Wind Speed (km/h)"),
        vertical_spacing=0.15,
    )
    area_colors = [
        ("#4fc3f7", "rgba(79,195,247,0.12)"),
        ("#81c784", "rgba(129,199,132,0.12)"),
        ("#ffb74d", "rgba(255,183,77,0.12)"),
        ("#ce93d8", "rgba(206,147,216,0.12)"),
    ]
    cols_map = [
        ("avg_temperature", 1, 1),
        ("avg_humidity", 1, 2),
        ("total_precipitation", 2, 1),
        ("avg_wind_speed", 2, 2),
    ]
    for i, (col, row, col_pos) in enumerate(cols_map):
        line_c, fill_c = area_colors[i]
        fig.add_trace(
            go.Scatter(
                x=df_daily["date"], y=df_daily[col],
                mode="lines",
                line=dict(color=line_c, width=2),
                fill="tozeroy",
                fillcolor=fill_c,
                name=col.replace("_", " ").title(),
                showlegend=False,
            ),
            row=row, col=col_pos,
        )

    fig.update_layout(
        paper_bgcolor="#0e1117",
        plot_bgcolor="#1a1f2e",
        font=dict(color="#e0e0e0", family="IBM Plex Mono"),
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    fig.update_xaxes(gridcolor="#2a3044", linecolor="#2a3044")
    fig.update_yaxes(gridcolor="#2a3044", linecolor="#2a3044")
    st.plotly_chart(fig, use_container_width=True)



# ROW: SEASONAL + HOURLY PATTERN
# ------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.markdown('<div class="section-header">Seasonal Breakdown</div>', unsafe_allow_html=True)
    seasonal = get_seasonal(selected_city)
    if seasonal:
        df_s = pd.DataFrame(seasonal)
        fig_s = go.Figure()
        fig_s.add_trace(go.Bar(
            x=df_s["season"],
            y=df_s["avg_temp"],
            marker_color=["#4fc3f7", "#81c784", "#ffb74d", "#ce93d8"],
            name="Avg Temp",
            text=df_s["avg_temp"].astype(str) + " °C",
            textposition="outside",
        ))
        fig_s.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            font=dict(color="#e0e0e0", family="IBM Plex Mono"),
            height=300, margin=dict(l=10, r=10, t=10, b=30),
            showlegend=False,
            yaxis_title="°C",
        )
        fig_s.update_xaxes(gridcolor="#2a3044")
        fig_s.update_yaxes(gridcolor="#2a3044")
        st.plotly_chart(fig_s, use_container_width=True)

with col_right:
    st.markdown('<div class="section-header">Hourly Temperature Pattern</div>', unsafe_allow_html=True)
    hourly = get_hourly_pattern(selected_city)
    if hourly:
        df_h = pd.DataFrame(hourly)
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(
            x=df_h["hour"], y=df_h["avg_temp"],
            mode="lines+markers",
            line=dict(color="#4fc3f7", width=2),
            marker=dict(size=6, color="#4fc3f7"),
            fill="tozeroy",
            fillcolor="rgba(79,195,247,0.08)",
        ))
        fig_h.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            font=dict(color="#e0e0e0", family="IBM Plex Mono"),
            height=300, margin=dict(l=10, r=10, t=10, b=30),
            showlegend=False,
            xaxis_title="Hour of Day",
            yaxis_title="°C",
        )
        fig_h.update_xaxes(gridcolor="#2a3044", dtick=3)
        fig_h.update_yaxes(gridcolor="#2a3044")
        st.plotly_chart(fig_h, use_container_width=True)



# ROW: CITY RANKINGS + ANOMALIES
# ------------------------------------------------------------------
col_a, col_b = st.columns([1, 2])

with col_a:
    st.markdown('<div class="section-header">City Rankings by AVG TEMP</div>', unsafe_allow_html=True)
    rankings = get_city_rankings()
    if rankings:
        df_r = pd.DataFrame(rankings)
        fig_r = go.Figure(go.Bar(
            x=df_r["avg_temp"],
            y=df_r["city_name"],
            orientation="h",
            marker=dict(
                color=df_r["avg_temp"],
                colorscale="RdYlBu_r",
                showscale=False,
            ),
            text=df_r["avg_temp"].astype(str) + " °C",
            textposition="outside",
        ))
        fig_r.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            font=dict(color="#e0e0e0", family="IBM Plex Mono"),
            height=max(300, 40 * len(df_r)),
            margin=dict(l=10, r=80, t=10, b=10),
            showlegend=False,
            xaxis_title="°C",
        )
        fig_r.update_xaxes(gridcolor="#2a3044")
        fig_r.update_yaxes(gridcolor="#2a3044")
        st.plotly_chart(fig_r, use_container_width=True)

with col_b:
    st.markdown('<div class="section-header">Temperature Anomalies</div>', unsafe_allow_html=True)
    anomalies = get_anomalies(selected_city, anomaly_limit)
    if anomalies:
        df_a = pd.DataFrame(anomalies)
        df_a["timestamp"] = pd.to_datetime(df_a["timestamp"])
        df_a["abs_deviation"] = df_a["deviation"].abs()

        fig_a = go.Figure()
        pos = df_a[df_a["deviation"] >= 0]
        neg = df_a[df_a["deviation"] < 0]
        for subset, color, name in [(pos, "#ff7043", "Above AVG"), (neg, "#4fc3f7", "Below avg")]:
            if not subset.empty:
                fig_a.add_trace(go.Scatter(
                    x=subset["timestamp"], y=subset["deviation"],
                    mode="markers",
                    marker=dict(
                        color=color,
                        size=subset["abs_deviation"].clip(5, 20),
                        opacity=0.8,
                        line=dict(width=0.5, color="#fff"),
                    ),
                    name=name,
                    hovertemplate=(
                        "<b>%{x}</b><br>"
                        "Temp: %{customdata[0]} °C<br>"
                        "Avg: %{customdata[1]} °C<br>"
                        "Deviation: %{y:.1f} °C<extra></extra>"
                    ),
                    customdata=subset[["temperature", "avg_temp"]].values,
                ))
        fig_a.add_hline(y=0, line_dash="dot", line_color="#8090a0", line_width=1)
        fig_a.update_layout(
            paper_bgcolor="#0e1117", plot_bgcolor="#1a1f2e",
            font=dict(color="#e0e0e0", family="IBM Plex Mono"),
            height=350, margin=dict(l=10, r=10, t=10, b=30),
            legend=dict(bgcolor="#1a1f2e", bordercolor="#2a3044"),
            xaxis_title="Date", yaxis_title="Deviation (°C)",
        )
        fig_a.update_xaxes(gridcolor="#2a3044")
        fig_a.update_yaxes(gridcolor="#2a3044", zeroline=False)
        st.plotly_chart(fig_a, use_container_width=True)

        with st.expander("Raw anomaly data"):
            st.dataframe(
                df_a[["timestamp", "temperature", "avg_temp", "deviation"]]
                .sort_values("deviation", key=abs, ascending=False)
                .reset_index(drop=True),
                use_container_width=True,
            )
    else:
        st.info("No anomalies found for this city")