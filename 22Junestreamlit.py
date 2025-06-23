# http://localhost:8514/

import streamlit as st
import pandas as pd
import plotly.express as px
import pymysql

# --- Config ---
st.set_page_config(page_title="Birds Monitoring Dashboard", layout="centered")
st.title("🕊️ Bird Monitoring Dashboard 🕊️")

# --- Load Data ---
@st.cache_data(show_spinner="Loading data...")
def load_data():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="birds_db"
    )
    df = pd.read_sql("""
        SELECT Plot_Name, Date, Observer, Common_Name, Scientific_Name, Distance,
               Sex, Temperature, Humidity, Sky, Wind, Start_Time, End_Time,
               PIF_Watchlist_Status
        FROM bird_monitoring
    """, conn)
    conn.close()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Year"] = df["Date"].dt.year
    df["Month"] = df["Date"].dt.strftime("%b")
    return df

df = load_data()

# --- Sidebar Filters ---
with st.sidebar:
    st.header("🔎 Filters")
    observers = st.multiselect("Observer", sorted(df["Observer"].dropna().unique()))
    plots = st.multiselect("Plot", sorted(df["Plot_Name"].dropna().unique()))
    species = st.multiselect("Species", sorted(df["Common_Name"].dropna().unique()))
    date_range = st.date_input("Date Range")

# --- Filtering ---
@st.cache_data(show_spinner=False)
def apply_filters(df, observers, plots, species, date_range):
    fdf = df.copy()
    if observers:
        fdf = fdf[fdf["Observer"].isin(observers)]
    if plots:
        fdf = fdf[fdf["Plot_Name"].isin(plots)]
    if species:
        fdf = fdf[fdf["Common_Name"].isin(species)]
    if isinstance(date_range, list) and len(date_range) == 2:
        fdf = fdf[
            (fdf["Date"] >= pd.to_datetime(date_range[0])) &
            (fdf["Date"] <= pd.to_datetime(date_range[1]))
        ]
    return fdf.reset_index(drop=True)

filtered_df = apply_filters(df, observers, plots, species, date_range)

# --- KPIs ---

k1, k2, k3 = st.columns(3)
k1.metric("Unique Species", filtered_df["Common_Name"].nunique())
k2.metric("Total Observations", len(filtered_df))
k3.metric("Unique Plots", filtered_df["Plot_Name"].nunique())

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Visualizations",
    "📅 Temporal Trends",
    "📁 Raw Data",
    "📈 Species Trends"
])

# --- TAB 1: General Visuals ---
with tab1:
    if filtered_df.empty:
        st.warning("No data to visualize.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🦜 Top 10 Species Distribution")
            pie_data = (
                filtered_df["Common_Name"]
                .value_counts()
                .nlargest(10)
                .reset_index(name="Count")
                .rename(columns={"index": "Common_Name"})
            )
            fig_pie = px.pie(pie_data, names="Common_Name", values="Count")
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.subheader("Species Observed by Observer")
            sb_data = filtered_df.sample(n=min(1000, len(filtered_df)))
            bar_data = (
                sb_data.groupby(["Observer", "Common_Name"])
                .size()
                .reset_index(name="Count")
            )
            fig_stacked_bar = px.bar(bar_data,x="Observer",y="Count",color="Common_Name",barmode="stack"
              
            
            )
            st.plotly_chart(fig_stacked_bar, use_container_width=True)

        st.subheader("🔵 Plot vs Species (Bubble Chart)")
        bubble_df = (
            filtered_df.groupby(["Plot_Name", "Common_Name"])
            .size()
            .reset_index(name="Count")
            .sort_values(by="Count", ascending=False)
            .head(100)
        )
        fig_bubble = px.scatter(
            bubble_df,
            x="Plot_Name",
            y="Common_Name",
            size="Count",
            color="Common_Name",
            title="Plot-wise Species Frequency",
            size_max=40
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

        st.subheader("📊 Top 15 Species")
        bar_df = (
            filtered_df["Common_Name"]
            .value_counts()
            .nlargest(15)
            .reset_index()
        )
        bar_df.columns = ["Common_Name", "Count"]
        fig_bar = px.bar(bar_df, x="Common_Name", y="Count", color="Common_Name", title="Top 15 Species Observed")
        st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("🌡️ Temperature vs Species")
        temp_df = filtered_df[["Temperature", "Common_Name"]].dropna().sample(n=min(1000, len(filtered_df)))
        fig_temp = px.scatter(
            temp_df,
            x="Temperature",
            y="Common_Name",
            color="Common_Name",
            title="Temperature vs Bird Observations"
        )
        st.plotly_chart(fig_temp, use_container_width=True)

        st.subheader("💧 Humidity vs Bird Count")
        humidity_df = (
            filtered_df.groupby("Humidity")["Common_Name"]
            .count()
            .reset_index(name="Observations")
        ).sort_values(by="Humidity")
        fig_humidity = px.line(humidity_df, x="Humidity", y="Observations", markers=True)
        st.plotly_chart(fig_humidity, use_container_width=True)

        if "PIF_Watchlist_Status" in filtered_df.columns:
            st.subheader("🚨 At-Risk Species (PIF Watchlist)")
            risk_df = filtered_df[filtered_df["PIF_Watchlist_Status"] > 0]
            if not risk_df.empty:
                risk_summary = (
                    filtered_df[filtered_df["PIF_Watchlist_Status"] != 0]["Common_Name"]
                    .value_counts()
                    .reset_index()
                )
                risk_summary.columns = ["Common_Name", "Count"]
                fig_risk = px.bar(risk_summary, x="Common_Name", y="Count", title="Watchlist Species")
                st.plotly_chart(fig_risk, use_container_width=True)
            else:
                st.info("No at-risk species in selected data.")

# --- TAB 2: Heatmap ---
with tab2:
    if filtered_df.empty:
        st.info("No data available for heatmap.")
    else:
        st.subheader("📆 Observation Heatmap by Month & Year")
        heatmap_df = (
            filtered_df.groupby(["Year", "Month"])
            .size()
            .reset_index(name="Observations")
        )
        pivot = heatmap_df.pivot(index="Month", columns="Year", values="Observations").fillna(0)
        pivot = pivot.reindex(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        fig_heatmap = px.imshow(
            pivot,
            labels=dict(x="Year", y="Month", color="Observations"),
            title="Bird Observations Over Time"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

# --- TAB 3: Raw Data ---
with tab3:
    st.subheader("📁 Filtered Data Table")
    st.dataframe(filtered_df.sample(n=min(len(filtered_df), 500)), use_container_width=True)
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", csv, "filtered_bird_data.csv", "text/csv")

# --- TAB 4: Species Trends ---
with tab4:
    st.subheader("📈 Species-Level Observation Trends")
    species_list = filtered_df["Common_Name"].dropna().unique()
    selected_species = st.multiselect("Select Species", species_list, max_selections=3)

    if selected_species:
        trend_df = filtered_df[filtered_df["Common_Name"].isin(selected_species)]

        st.subheader("📆 Year-wise Trends")
        yearly = trend_df.groupby(["Year", "Common_Name"]).size().reset_index(name="Count")
        fig_year = px.line(yearly, x="Year", y="Count", color="Common_Name", markers=True)
        st.plotly_chart(fig_year, use_container_width=True)

        st.subheader("📅 Date-wise Trends (Recent 1000)")
        datewise = (
            trend_df
            .sort_values("Date")
            .groupby(["Date", "Common_Name"])
            .size()
            .reset_index(name="Count")
            .sort_values("Date")
            .tail(1000)
        )
        fig_date = px.line(datewise, x="Date", y="Count", color="Common_Name", markers=True)
        st.plotly_chart(fig_date, use_container_width=True)
    else:
        st.info("Select species to view trend charts.")
