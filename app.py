from src.io import load_all_games
from src.transforms import (
    make_placement_df,
    make_avg_prog_df,
    make_turns_df,
    make_master_df
)
from src.plots import (
    plot_stacked_bar,
    plot_one_game,
    plot_firsts,
    plot_grouped_bar,
    plot_length_hist,
    pi_series,
    plot_robbed
)
from src.helpers import render_hex, kpi, time_dict, make_firsts_df

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

div[data-testid="stPlotlyChart"] {
    display: flex !important;
    justify-content: flex-start !important;
}

div[data-testid="stPlotlyChart"] > div {
    width: 100% !important;
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
num_games = values[0]

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
    width='stretch'
)

st.markdown("""
    <div style='font-size:28px; font-weight:600;
    font-family: Bahnschrift, Segoe UI;'>
    <span style='color:#d4af37;'>Winners</span>
    city up and take longest road
    </div>
""", unsafe_allow_html=True)
st.markdown("""
    <div style='font-size:20px; font-weight:600;
    font-family: Bahnschrift, Segoe UI;'>
    Average VPs gain from different sources in comparison to
    <span style='color:#B0B7C0;'>runner up,</span>
    <span style='color:#B87333;'>player in third,</span>  
    and
    <span style='color:#3c78d8;'>player in fourth,</span>     
    </div>
""", unsafe_allow_html=True)
st.plotly_chart(
    plot_grouped_bar(master),
    width='stretch'
)

col1, col2 = st.columns([3, 2], gap="small")

with col1:
    st.markdown("""
        <div style='font-size:28px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        Is the snake draft really fair?
        </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
        <div style='font-size:20px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        How players in different placement orders fared across <b>{num_games}</b> games
        </div>
    """, unsafe_allow_html=True)  
    st.plotly_chart(plot_stacked_bar(master), width='stretch')
with col2:
    st.markdown("""
        <div style='font-size:28px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        How long do games last?
        </div>
    """, unsafe_allow_html=True)
    st.markdown("""
        <div style='font-size:20px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        Distribution of game length in turns
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(plot_length_hist(turns))

col1, col2 = st.columns([3, 1], gap="small", vertical_alignment="bottom")

firsts_df = make_firsts_df(turns)
with col1:
    st.markdown("""
        <div style='font-size:28px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        How early in the game are key milestones achieved?
        </div>
    """, unsafe_allow_html=True)
    st.markdown("""
        <div style='font-size:20px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        Kernel density estimates of key actions for each player by rank
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(plot_firsts(firsts_df), width='stretch', config={"displayModeBar": False})

with col2:
    st.plotly_chart(pi_series(firsts_df), width='stretch', config={"displayModeBar": False})


st.markdown("""
        <div style='font-size:28px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        Target on your back: can taking the lead too early set you up for failure?
        </div>
    """, unsafe_allow_html=True)
st.markdown("""
        <div style='font-size:20px; font-weight:600;
        font-family: Bahnschrift, Segoe UI;'>
        Distribution of robber disparities between winning player and runner-up
        </div>
    """, unsafe_allow_html=True)
st.plotly_chart(plot_robbed(master, turns),  width='stretch', config={"displayModeBar": False})
#st.pyplot(plot_avg_prog(progress))