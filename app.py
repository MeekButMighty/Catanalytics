from src.io import load_all_games
#from src.transforms import game_cropper, count_dcs, rank_players, update_turns_df
from src.transforms import make_placement_df, make_avg_prog_df, make_turns_df, make_master_df
from src.plots import plot_stacked_bar, plot_avg_prog, plot_one_game, plot_firsts, plot_grouped_bar
from src.helpers import render_hex, kpi

import streamlit as st

st.set_page_config(
    page_title="Catanalytics",
    layout="wide"
)

color_dict = {
    1: '#D4AF37',  # Gold
    2: '#B0B7C0',  # Silver
    3: '#B87333',  # Bronze
    4: '#3c78d8'   # Rose
}

st.markdown("""
<style>
html, body, [data-testid="stApp"] {
    font-family: 'Bahnschrift', 'Segoe UI', sans-serif;
}

/* Streamlit titles */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Bahnschrift', 'Segoe UI', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([3, 3], vertical_alignment="center")

with col1:
    st.title("CATANALYTICS")
    st.subheader("A personal data project by Oliver Meek")
    st.markdown("Data displayed on this dashboard was scraped from the online version of Catan, [colonist.io](https://colonist.io). To view the code involved in production, access the github repo [here](https://github.com/MeekButMighty/CatanAnalytics/tree/main).")

with col2:
    st.image("dash_logo.png")#, width=350)



raw_df = load_all_games()

master = make_master_df(raw_df)
turns = make_turns_df(raw_df)
progress = make_avg_prog_df(turns)


k1, k2, k3, k4, k5 = st.columns(5)
values = kpi(master, turns)
with k1:
    render_hex("Games Analyzed", values[0])

with k2:
    render_hex("Turns analyzed", values[1])
    
with k3:
    render_hex("Players in\nSystem", values[2])

with k4:
    render_hex("MadmanMeek win rate", values[3])

with k5:
    render_hex("MadmanMeek average VPs", values[4])

st.plotly_chart(plot_one_game(turns, master))
st.plotly_chart(plot_grouped_bar(master))
st.pyplot(plot_stacked_bar(master))
st.pyplot(plot_firsts(turns, 2))
st.pyplot(plot_avg_prog(progress))