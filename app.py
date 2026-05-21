from src.io import load_all_games
from src.transforms import (
    make_placement_df,
    make_avg_prog_df,
    make_turns_df,
    make_master_df
)
from src.plots import (
    plot_stacked_bar,
    plot_avg_prog,
    plot_one_game,
    plot_firsts,
    plot_grouped_bar
)
from src.helpers import render_hex, kpi, time_dict

import streamlit as st

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(
    page_title="Catanalytics",
    layout="wide"
)

color_dict = {
    1: '#D4AF37',
    2: '#B0B7C0',
    3: '#B87333',
    4: '#3c78d8'
}

# -------------------------
# GLOBAL STYLE (cached once)
# -------------------------
st.markdown("""
<style>
html, body, [data-testid="stApp"] {
    font-family: 'Bahnschrift', 'Segoe UI', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Bahnschrift', 'Segoe UI', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)


# -------------------------
# CACHED DATA PIPELINE
# -------------------------
@st.cache_data
def load_data():
    raw_df = load_all_games()
    master = make_master_df(raw_df)
    turns = make_turns_df(raw_df)
    progress = make_avg_prog_df(turns)
    return master, turns, progress


@st.cache_data
def get_timestamp_options(turns):
    return time_dict(turns)


@st.cache_data
def get_kpis(master, turns):
    return kpi(master, turns)


# -------------------------
# LOAD DATA (cached)
# -------------------------
master, turns, progress = load_data()


# -------------------------
# HEADER
# -------------------------
col1, col2 = st.columns([3, 3], vertical_alignment="center")

with col1:
    st.title("CATANALYTICS")
    st.subheader("A personal data project by Oliver Meek")
    st.markdown(
        "Data displayed on this dashboard was scraped from "
        "[colonist.io](https://colonist.io). "
        "To view the code involved in production, access the github repo [here](https://github.com/MeekButMighty/Catanalytics)."
    )

with col2:
    st.image("dash_logo.png")


# -------------------------
# KPI ROW (cached)
# -------------------------
values = get_kpis(master, turns)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    render_hex("Games Analyzed", values[0])

with k2:
    render_hex("Turns analyzed", values[1])

with k3:
    render_hex("Players in System", values[2])

with k4:
    render_hex("MadmanMeek win rate", values[3])

with k5:
    render_hex("MadmanMeek average VPs", values[4])


# -------------------------
# TIMESTAMP OPTIONS (cached)
# -------------------------
timestamp_options = get_timestamp_options(turns)


# -------------------------
# SELECT + TITLE ROW
# -------------------------
col1, col2 = st.columns([10, 14], gap="small")

with col1:
    st.markdown("<div style='height:44px'></div>", unsafe_allow_html=True)
    st.markdown("""
        <div style='font-size:28px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        VP Progression for game played on:
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("<div style='height:44px'></div>", unsafe_allow_html=True)

    selected_label = st.selectbox(
        "Select game",
        options=list(timestamp_options.keys()),
        label_visibility="collapsed"
    )

selected_timestamp = timestamp_options[selected_label]


# -------------------------
# PLOTS
# -------------------------
st.plotly_chart(
    plot_one_game(turns, master, selected_timestamp),
    use_container_width=True
)

st.plotly_chart(
    plot_grouped_bar(master),
    use_container_width=True
)

st.pyplot(plot_stacked_bar(master))
st.pyplot(plot_firsts(turns, 2))
st.pyplot(plot_avg_prog(progress))