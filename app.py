import os
import glob
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# =============================================================================
# PAGE CONFIG + STYLING
# =============================================================================
st.set_page_config(
    layout="wide",
    page_title="AIRWISE – India Air Quality Intelligence Dashboard",
    page_icon="A",
)

st.markdown("""
<style>
.main-banner{
    padding: 1.6rem 2rem;
    border-radius: 16px;
    background: linear-gradient(120deg,#0f2027,#203a43,#2c5364);
    color: white;
    margin-bottom: 1.2rem;
}
.main-banner h1{margin:0;font-size:2.1rem;}
.main-banner p{margin:0.3rem 0 0 0;opacity:0.85;font-size:0.95rem;}
.kpi-card{
    background: white;
    border-radius: 14px;
    padding: 1rem 1.2rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    border-left: 6px solid #2c5364;
}
.kpi-card h4{margin:0;font-size:0.8rem;color:#666;font-weight:600;text-transform:uppercase;letter-spacing:.03em;}
.kpi-card .val{font-size:1.6rem;font-weight:700;color:#0f2027;margin-top:.25rem;}
.section-title{
    font-size:1.35rem;font-weight:700;color:#0f2027;
    border-bottom:3px solid #2c5364;padding-bottom:.35rem;margin:.5rem 0 1rem 0;
}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.75rem;font-weight:700;color:white;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-banner">
<h1>AIRWISE — India Air Quality Intelligence Dashboard</h1>
<p>Interactive exploration of pollutant levels across Indian states, cities and monitoring stations.</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# AQI-STYLE CATEGORY HELPERS
# CPCB category breakpoints are used for PM2.5 / PM10 (µg/m³, well-established
# units in this dataset). Other pollutants use dataset-relative quartiles
# labeled clearly as "relative level" since exact reporting units vary.
# =============================================================================
CATEGORY_COLORS = {
    "Good": "#2ecc71",
    "Satisfactory": "#a3e048",
    "Moderate": "#f1c40f",
    "Poor": "#e67e22",
    "Very Poor": "#e74c3c",
    "Severe": "#8e44ad",
    "Low": "#2ecc71",
    "High": "#e67e22",
    "Very High": "#8e44ad",
}

def cpcb_category(pollutant, value):
    if pd.isna(value):
        return None
    if pollutant == "PM2.5":
        bounds = [(30, "Good"), (60, "Satisfactory"), (90, "Moderate"),
                  (120, "Poor"), (250, "Very Poor")]
    elif pollutant == "PM10":
        bounds = [(50, "Good"), (100, "Satisfactory"), (250, "Moderate"),
                  (350, "Poor"), (430, "Very Poor")]
    else:
        return None
    for limit, label in bounds:
        if value <= limit:
            return label
    return "Severe"

def add_category_column(df):
    df = df.copy()
    categories = []
    for pol, val in zip(df["pollutant_id"], df["pollutant_avg"]):
        official = cpcb_category(pol, val)
        categories.append(official)
    df["aqi_category"] = categories

    # For pollutants without an official CPCB category here, fall back to
    # dataset-relative quartiles per pollutant so every row still gets a label.
    missing_mask = df["aqi_category"].isna()
    if missing_mask.any():
        for pol in df.loc[missing_mask, "pollutant_id"].unique():
            sub = df["pollutant_id"] == pol
            q1, q2, q3 = df.loc[sub, "pollutant_avg"].quantile([0.25, 0.5, 0.75])
            def relative_label(v):
                if v <= q1:
                    return "Low"
                elif v <= q3:
                    return "Moderate"
                else:
                    return "High" if v <= q3 + (q3 - q1) else "Very High"
            df.loc[sub & missing_mask, "aqi_category"] = df.loc[sub & missing_mask, "pollutant_avg"].apply(relative_label)
    return df

# =============================================================================
# ROBUST DATA LOADING — handles filename variations (spaces vs underscores,
# case, upload folder) instead of hard-failing on one exact name.
# =============================================================================
@st.cache_data
def load_and_clean_data(uploaded_bytes=None):
    df = None
    if uploaded_bytes is not None:
        df = pd.read_csv(uploaded_bytes)
    else:
        candidates = [
            "Air quality in india.csv",
            "Air_quality_in_india.csv",
            "air_quality_in_india.csv",
        ]
        found_path = None
        for c in candidates:
            if os.path.exists(c):
                found_path = c
                break
        if found_path is None:
            # Fuzzy fallback: normalize filenames and look for a match
            for path in glob.glob("*.csv"):
                norm = path.lower().replace(" ", "").replace("_", "")
                if norm == "airqualityinindia.csv":
                    found_path = path
                    break
        if found_path is None:
            return None
        df = pd.read_csv(found_path)

    # Strip stray whitespace from text columns
    for col in ["state", "city", "station", "pollutant_id"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Impute missing pollutant values with column median
    for col in ["pollutant_min", "pollutant_max", "pollutant_avg"]:
        if col in df.columns and df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())

    # Parse timestamp
    df["last_update"] = pd.to_datetime(df["last_update"], format="%d-%m-%Y %H:%M:%S", errors="coerce")
    df = df.dropna(subset=["last_update"])
    df["date"] = df["last_update"].dt.date

    df = add_category_column(df)
    return df

df = load_and_clean_data()

if df is None:
    st.error("Couldn't automatically find the air quality CSV in the app folder.")
    uploaded = st.file_uploader("Upload the dataset CSV to continue", type="csv")
    if uploaded is not None:
        df = load_and_clean_data(uploaded)
    if df is None:
        st.stop()

# Is this a genuine time series, or a single-timestamp snapshot (as in this dataset)?
IS_SNAPSHOT = df["last_update"].nunique() <= 1
SNAPSHOT_TIME = df["last_update"].iloc[0] if IS_SNAPSHOT else None

# =============================================================================
# SIDEBAR FILTERS
# =============================================================================
st.sidebar.header("Filters")

all_states = sorted(df["state"].unique().tolist())
all_pollutants = sorted(df["pollutant_id"].unique().tolist())
default_idx = all_pollutants.index("PM2.5") if "PM2.5" in all_pollutants else 0

# Pollutant first, since it drives most panels
selected_pollutant = st.sidebar.selectbox("Pollutant", all_pollutants, index=default_idx)

st.sidebar.markdown("**Location scope**")
scope = st.sidebar.radio(
    "Scope", ["All India", "Specific state(s)", "Specific city(ies)"],
    label_visibility="collapsed",
)

if scope == "All India":
    selected_states = all_states
    selected_cities = sorted(df["city"].unique().tolist())

elif scope == "Specific state(s)":
    selected_states = st.sidebar.multiselect(
        "Choose state(s)", all_states,
        help="Start typing to search a state.",
    )
    if not selected_states:
        st.sidebar.caption("No state chosen yet — showing all of India.")
        selected_states = all_states
    selected_cities = sorted(df[df["state"].isin(selected_states)]["city"].unique().tolist())

else:  # Specific city(ies)
    selected_cities = st.sidebar.multiselect(
        "Choose city(ies)", sorted(df["city"].unique().tolist()),
        help="Start typing to search a city.",
    )
    if not selected_cities:
        st.sidebar.caption("No city chosen yet — showing all cities.")
        selected_cities = sorted(df["city"].unique().tolist())
    selected_states = sorted(df[df["city"].isin(selected_cities)]["state"].unique().tolist())

st.sidebar.divider()
st.sidebar.caption(
    f"Data snapshot: {SNAPSHOT_TIME}" if IS_SNAPSHOT else "Multi-date dataset detected"
)
st.sidebar.caption(f"Rows loaded: {len(df):,} | States: {len(selected_states)} | Cities: {len(selected_cities)}")

df_f = df[df["state"].isin(selected_states) & df["city"].isin(selected_cities)]
df_pol = df_f[df_f["pollutant_id"] == selected_pollutant]

if IS_SNAPSHOT:
    st.info(
        f"This dataset is a single real-time snapshot (all readings timestamped "
        f"{SNAPSHOT_TIME}), not a historical time series — so trend-over-time charts aren't "
        f"meaningful here. The views below focus on the geographic and comparative patterns "
        f"the data actually supports."
    )

tab_overview, tab_map, tab_pollutant, tab_compare, tab_insights = st.tabs(
    ["Overview", "Map", "Pollutant Analysis", "State & City Comparison", "Insights"]
)

# =============================================================================
# TAB 1 — OVERVIEW
# =============================================================================
with tab_overview:
    st.markdown('<div class="section-title">National Overview</div>', unsafe_allow_html=True)

    if df_f.empty:
        st.warning("No data for the selected filters.")
    else:
        state_means = df_f.groupby("state")["pollutant_avg"].mean()
        city_means = df_f.groupby("city")["pollutant_avg"].mean()
        overall_avg = df_f["pollutant_avg"].mean()
        state_highest, val_highest = state_means.idxmax(), state_means.max()
        city_lowest, val_lowest = city_means.idxmin(), city_means.min()
        most_common_pollutant = df_f["pollutant_id"].mode().iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        for col, label, val in zip(
            [c1, c2, c3, c4],
            [f"Overall Avg {selected_pollutant}", f"Highest Avg {selected_pollutant} State",
             f"Lowest Avg {selected_pollutant} City", "Most Prevalent Pollutant"],
            [f"{overall_avg:.1f}", f"{state_highest} ({val_highest:.1f})",
             f"{city_lowest} ({val_lowest:.1f})", most_common_pollutant],
        ):
            col.markdown(f'<div class="kpi-card"><h4>{label}</h4><div class="val">{val}</div></div>', unsafe_allow_html=True)

        st.write("")

        left, right = st.columns([3, 2])
        with left:
            st.subheader(f"Top 15 Stations by {selected_pollutant} Level")
            top_stations = (
                df_pol.groupby(["station", "city"])["pollutant_avg"].mean()
                .reset_index().sort_values("pollutant_avg", ascending=False).head(15)
            )
            top_stations["aqi_category"] = top_stations["pollutant_avg"].apply(
                lambda v: cpcb_category(selected_pollutant, v) or "Moderate"
            )
            fig = px.bar(
                top_stations, x="pollutant_avg", y="station", color="aqi_category",
                orientation="h", hover_data=["city"],
                color_discrete_map=CATEGORY_COLORS,
                labels={"pollutant_avg": f"{selected_pollutant} level", "station": ""},
                template="plotly_white",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=480)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            st.subheader(f"{selected_pollutant} Category Breakdown")
            cat_counts = df_pol["aqi_category"].value_counts().reset_index()
            cat_counts.columns = ["category", "count"]
            fig_donut = px.pie(
                cat_counts, names="category", values="count", hole=0.5,
                color="category", color_discrete_map=CATEGORY_COLORS, template="plotly_white",
            )
            fig_donut.update_traces(textinfo="percent+label")
            fig_donut.update_layout(height=480, showlegend=False)
            st.plotly_chart(fig_donut, use_container_width=True)

# =============================================================================
# TAB 2 — MAP
# =============================================================================
with tab_map:
    st.markdown('<div class="section-title">Geographic Distribution</div>', unsafe_allow_html=True)

    map_pollutant = st.selectbox("Pollutant for map", all_pollutants, index=default_idx, key="map_pollutant")
    color_mode = st.radio("Color by", ["Concentration (continuous)", "AQI-style category"], horizontal=True)

    df_map = (
        df_f[df_f["pollutant_id"] == map_pollutant]
        .groupby(["state", "city", "latitude", "longitude"], dropna=True)
        .agg(pollutant_avg=("pollutant_avg", "mean"))
        .reset_index()
    )
    df_map["latitude"] = pd.to_numeric(df_map["latitude"], errors="coerce")
    df_map["longitude"] = pd.to_numeric(df_map["longitude"], errors="coerce")
    df_map["pollutant_avg"] = pd.to_numeric(df_map["pollutant_avg"], errors="coerce")
    df_map = df_map.dropna(subset=["latitude", "longitude", "pollutant_avg"]).copy()

    if df_map.empty:
        st.info("No data to display on the map for the current filters.")
    else:
        min_v, max_v = df_map["pollutant_avg"].min(), df_map["pollutant_avg"].max()
        if pd.notna(min_v) and pd.notna(max_v) and max_v > min_v:
            df_map["marker_size"] = 8 + 22 * (df_map["pollutant_avg"] - min_v) / (max_v - min_v)
        else:
            df_map["marker_size"] = 14.0
        df_map["marker_size"] = (
            pd.to_numeric(df_map["marker_size"], errors="coerce")
            .replace([np.inf, -np.inf], np.nan).fillna(14.0).clip(6, 30)
        )

        map_kwargs = dict(
            data_frame=df_map, lat="latitude", lon="longitude", size="marker_size",
            hover_name="city",
            hover_data={"state": True, "pollutant_avg": ":.2f", "marker_size": False,
                        "latitude": False, "longitude": False},
            zoom=3.6, height=620, title=f"Average {map_pollutant} Levels Across India",
        )
        if color_mode.startswith("Concentration"):
            df_map_plot = df_map
            map_kwargs.update(color="pollutant_avg", color_continuous_scale=px.colors.sequential.Turbo,
                               data_frame=df_map_plot)
        else:
            df_map["aqi_category"] = df_map["pollutant_avg"].apply(
                lambda v: cpcb_category(map_pollutant, v) or "Moderate"
            )
            map_kwargs.update(color="aqi_category", color_discrete_map=CATEGORY_COLORS, data_frame=df_map)

        if hasattr(px, "scatter_map"):
            fig_map = px.scatter_map(**map_kwargs)
            fig_map.update_layout(map_style="carto-positron")
        else:
            fig_map = px.scatter_mapbox(**map_kwargs)
            fig_map.update_layout(mapbox_style="carto-positron")
        fig_map.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

# =============================================================================
# TAB 3 — POLLUTANT ANALYSIS
# =============================================================================
with tab_pollutant:
    st.markdown('<div class="section-title">Pollutant Analysis</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.warning("No data for the current filters.")
    else:
        avg_by_state_pol = df_f.groupby(["state", "pollutant_id"])["pollutant_avg"].mean().reset_index()
        fig1 = px.bar(
            avg_by_state_pol, x="state", y="pollutant_avg", color="pollutant_id",
            barmode="group", template="plotly_white",
            title="Average Pollutant Levels by State",
            labels={"pollutant_avg": "Average level"},
        )
        fig1.update_layout(height=460, xaxis_tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.box(
            df_f, x="pollutant_id", y="pollutant_avg", color="pollutant_id",
            template="plotly_white", title="Distribution of Pollutant Levels",
            labels={"pollutant_avg": "Level"},
        )
        fig2.update_layout(height=460, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

# =============================================================================
# TAB 4 — STATE & CITY COMPARISON
# =============================================================================
with tab_compare:
    st.markdown('<div class="section-title">State &amp; City Comparison</div>', unsafe_allow_html=True)
    if df_pol.empty:
        st.warning("No data for the current filters.")
    else:
        search = st.text_input("Jump to a city (optional)")
        city_comp = df_pol.groupby("city")["pollutant_avg"].mean().sort_values(ascending=False).reset_index()

        if search:
            hit = city_comp[city_comp["city"].str.contains(search, case=False, na=False)]
            if not hit.empty:
                st.success(f"**{hit.iloc[0]['city']}**: average {selected_pollutant} = {hit.iloc[0]['pollutant_avg']:.2f}")
            else:
                st.warning("City not found in current filters.")

        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Top 10 Cities — Highest Avg {selected_pollutant}**")
            fig_top = px.bar(city_comp.head(10), x="pollutant_avg", y="city", orientation="h",
                              color_discrete_sequence=["#e74c3c"], template="plotly_white")
            fig_top.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
            st.plotly_chart(fig_top, use_container_width=True)
        with c2:
            st.write(f"**Bottom 10 Cities — Lowest Avg {selected_pollutant}**")
            fig_bot = px.bar(city_comp.tail(10).sort_values("pollutant_avg"), x="pollutant_avg", y="city",
                              orientation="h", color_discrete_sequence=["#2ecc71"], template="plotly_white")
            fig_bot.update_layout(yaxis={"categoryorder": "total ascending"}, height=420)
            st.plotly_chart(fig_bot, use_container_width=True)

        state_avg = df_pol.groupby("state")["pollutant_avg"].mean().reset_index().sort_values("pollutant_avg", ascending=False)
        fig_state = px.bar(state_avg, x="state", y="pollutant_avg", template="plotly_white",
                            title=f"Average {selected_pollutant} by State",
                            color="pollutant_avg", color_continuous_scale="Turbo")
        fig_state.update_layout(height=440, xaxis_tickangle=-45)
        st.plotly_chart(fig_state, use_container_width=True)

        st.download_button(
            "Download filtered data (CSV)",
            df_f.to_csv(index=False).encode("utf-8"),
            file_name="airwise_filtered_data.csv",
            mime="text/csv",
        )

# =============================================================================
# TAB 5 — INSIGHTS
# =============================================================================
with tab_insights:
    st.markdown('<div class="section-title">Data-Driven Insights</div>', unsafe_allow_html=True)
    if df_f.empty:
        st.warning("No data for the current filters.")
    else:
        insights = []

        if IS_SNAPSHOT:
            insights.append(f"This dataset is a single snapshot taken at **{SNAPSHOT_TIME}** across all stations — there is no time trend to report.")
        else:
            over_time = df_pol.groupby("date")["pollutant_avg"].mean().reset_index()
            if len(over_time) > 1:
                first, last = over_time["pollutant_avg"].iloc[0], over_time["pollutant_avg"].iloc[-1]
                direction = "increased" if last > first else "decreased" if last < first else "stayed stable"
                insights.append(f"Average **{selected_pollutant}** {direction} from {first:.2f} to {last:.2f} over the observed period.")

        state_avg_all = df_f.groupby(["state", "pollutant_id"])["pollutant_avg"].mean().reset_index()
        top_row = state_avg_all.loc[state_avg_all["pollutant_avg"].idxmax()]
        insights.append(f"**{top_row['state']}** shows the highest average for **{top_row['pollutant_id']}** at **{top_row['pollutant_avg']:.2f}**.")

        overall_top_pollutant = df_f.groupby("pollutant_id")["pollutant_avg"].mean().idxmax()
        insights.append(f"Across selected regions, **{overall_top_pollutant}** has the highest average concentration overall.")

        if not df_pol.empty:
            ranges = df_pol.groupby("city").apply(lambda g: g["pollutant_max"].max() - g["pollutant_min"].min())
            if not ranges.empty:
                widest_city = ranges.idxmax()
                insights.append(f"**{widest_city}** shows the widest spread in **{selected_pollutant}** readings across its stations.")

        severe_share = (df_pol["aqi_category"].isin(["Poor", "Very Poor", "Severe"]).mean() * 100) if not df_pol.empty else 0
        insights.append(f"**{severe_share:.1f}%** of {selected_pollutant} readings fall in Poor/Very Poor/Severe categories under current filters.")

        for i in insights:
            st.info(i)

st.markdown("---")
st.caption("AIRWISE · Built with Streamlit, Pandas & Plotly · IBM Internship / GitHub Portfolio project")
