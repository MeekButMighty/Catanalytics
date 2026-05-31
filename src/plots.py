import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde
from src.helpers import p2_lead_pct

color_dict = {
    1: '#D4AF37',  # Gold
    2: '#B0B7C0',  # Silver
    3: '#B87333',  # Bronze
    4: '#3c78d8',   # Rose
    5: '#38761d'   # Green (for 5+ player games)
}

def plot_grouped_bar(master_df):
    vp_breakdown = master_df[['rank', 'vp_settle', 'vp_city', 'vp_dc', 'longest_road', 'largest_army']].copy()
    vp_breakdown['rank']=vp_breakdown['rank'].astype(str)
    vp_breakdown = vp_breakdown.groupby('rank').mean()
    vp_breakdown = (
        vp_breakdown
        .reset_index()
        .melt(
            id_vars='rank',
            var_name='vp_type',
            value_name='average'
        )
    )
    vp_breakdown['vp_type'] = vp_breakdown['vp_type'].map({
        'vp_settle': 'Settlements',
        'vp_city': 'Cities',
        'vp_dc': 'Dev Cards',
        'longest_road': 'Longest Road',
        'largest_army': 'Largest Army'
    })
    fig = px.bar(
        vp_breakdown,
        x='vp_type',
        y='average',
        color='rank',
        barmode='group',
        color_discrete_map={str(k): v for k, v in color_dict.items()},
    )

    fig.update_yaxes(tickvals=[0, 1, 2, 3, 4])

    fig.update_layout(
        yaxis_title="",
        xaxis_title="",
        yaxis=dict(
            automargin=False
        ),
        height=350,
        showlegend=False,
        margin=dict(
            t=10,   # reduce top margin
            l=20,
            r=20,
            b=20
        )
    )
    
    return fig

def plot_length_hist(turns_df):
    final_turns = turns_df[turns_df['game_percentage']==1.0].copy()
    lengths = final_turns['turn']
    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=lengths,
            nbinsx=12,
            marker_color=color_dict[5]
        )
    )
    fig.update_layout(
        height=332,
        margin=dict(t=20, b=40),
        xaxis=dict(
             title="Turns"
        )
    )

    return fig

def plot_one_game(turns_df, master_df, timestamp):

    # filter to selected game timestamp
    d = turns_df[turns_df["timestamp"] == timestamp]

    # get matching game_id
    gid = d["game_id"].iloc[0]

    # get players for this game
    players = (
        master_df[master_df['game_id'] == gid]['player']
        .unique()
    )

    fig = go.Figure()

    for placement, player in zip(
        ['p1_vps', 'p2_vps', 'p3_vps', 'p4_vps'],
        players
    ):

        fig.add_trace(go.Scatter(
            x=d['turn'],
            y=d[placement],
            mode="lines",
            name=player,
            line=dict(
                color=color_dict[
                    np.where(players == player)[0][0] + 1
                ]
            )
        ))

    fig.update_layout(
        legend=dict(
            x=0.04,
            y=0.92,
            xanchor="left",
            yanchor="top"
        ),
        xaxis_title="Turn",
        yaxis=dict(
            automargin=False
        ),
        margin=dict(
            t=10,   # reduce top margin
            l=20,
            r=20,
            b=20
        )
    )

    return fig

def plot_stacked_bar(master_df):

    summary = (
        master_df
        .groupby(["placement_order", "rank"])
        .size()
        .reset_index(name="count")
    )

    summary["value"] = (
        summary["count"]
        / summary.groupby("placement_order")["count"].transform("sum")
    )

    plot_df = (
        summary
        .pivot(
            index="placement_order",
            columns="rank",
            values="value"
        )
        .fillna(0)
        .sort_index()
    )

    fig = go.Figure()

    # add one horizontal stacked bar trace per rank
    for rank in plot_df.columns:
        fig.add_trace(
            go.Bar(
                y=plot_df.index,
                x=plot_df[rank],
                name=f"Rank {rank}",
                orientation="h",
                marker_color=color_dict[rank],
                hovertemplate=(
                    f"Rank: {rank}<br>"
                    "Placement Order: %{y}<br>"
                    "Proportion: %{x:.1%}<extra></extra>"
                )
            )
        )

    fig.update_layout(
        barmode="stack",
        height=350,
        width=800,
        showlegend=False,

        # reverse y-axis like invert_yaxis()
        yaxis=dict(
            autorange="reversed",
            tickmode="array",
            tickvals=[4, 3, 2, 1],
            ticktext=[
                "4th, 5th",
                "3rd, 6th",
                "2nd, 7th",
                "1st, 8th"
            ],
            tickfont=dict(size=19),
            title="",
            automargin=False
        ),

        xaxis=dict(
            range=[0, 1],
            tickmode="array",
            tickvals=[0, 0.25, 0.5, 0.75, 1.0],
            ticktext=["0%", "25%", "50%", "75%", "100%"],
            title="Proportion of games"
        ),
        margin=dict(l=80, r=40, t=20, b=40),
    )

    return fig

def plot_firsts(firsts_df):
    #reshape to long format
    def melt_action(df, keyword):

        cols = [f'p{i}_{keyword}' for i in range(1, 5)]

        long_df = df.melt(
            id_vars="game_id",
            value_vars=cols,
            var_name="player",
            value_name="turn"
        ).dropna()

        long_df["player"] = (
            long_df["player"]
            .str.extract(r"p(\d)")[0]
            .astype(int)
        )
        return long_df

    settle_long = melt_action(firsts_df, "first_settle")
    city_long = melt_action(firsts_df, "first_city")
    dc_long = melt_action(firsts_df, "first_dc")

    legend_labels = {
        1: "Winner",
        2: "Runner-up",
        3: "3rd Place",
        4: "4th Place"
    }
    #KDE helper
    def add_kde_trace(fig, df, row, title):
        x_grid = np.linspace(0, 1, 500)
        for player in sorted(df["player"].unique()):
            vals = df[df["player"] == player]["turn"].dropna()
            if len(vals) < 2:
                continue
            kde = gaussian_kde(vals, bw_method=0.25)
            y = kde(x_grid)
            fig.add_trace(
                go.Scatter(
                    x=x_grid,
                    y=y,
                    mode='lines',
                    line=dict(
                        width=1.5,
                        color=color_dict[player]
                    ),
                    fill='tozeroy',
                    opacity=0.40,
                    name= legend_labels[player],
                    legendgroup=f"player_{player}",
                    # only show legend once
                    showlegend=(row == 1),
                    # players 3+ start hidden
                    visible=True if player in [1, 2] else "legendonly"
                ),
                row=row,
                col=1
            )

        fig.add_annotation(
            text=title,
            x=-0.032,
            y=1.2,
            xref="paper",
            yref=f"y{row} domain" if row > 1 else "y domain",
            showarrow=False,
            font=dict(size=16, family="Bahnschrift, Segoe UI, Arial")
        )

    #plot data
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08
    )

    add_kde_trace(fig, settle_long, 1, "First Settlement Built (not including starting settlements)")
    add_kde_trace(fig, city_long, 2, "First City Built")
    add_kde_trace(fig, dc_long, 3, "First Dev Card Drawn")

    fig.update_layout(
        height=500,
        margin=dict(t=40, l=0, r=20, b=40),

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="right",
            x=1,
            title=""
        ),

        hovermode="x unified"
    )

    fig.update_xaxes(
        range=[0, 1],
        showgrid=True,
        gridwidth=1,
        tickvals=[0, 0.25, 0.5, 0.75, 1],
        ticktext=['0%', '25%', '50%', '75%', '100%']
    )
    

    fig.update_xaxes(
        title_text="Percentage of Game Completed",
        row=3,
        col=1
    )

    return fig

def pi_series(firsts_df):

    metrics = [
        (
            [f"p{i}_first_settle" for i in range(1, 5)],
            "Who built the first settlement?"
        ),
        (
            [f"p{i}_first_city" for i in range(1, 5)],
            "Who built the first city?"
        ),
        (
            [f"p{i}_first_dc" for i in range(1, 5)],
            "Who bought the first dev card?"
        )
    ]

    fig = make_subplots(
        rows=3,
        cols=1,
        specs=[[{"type": "pie"}]] * 3,
        subplot_titles=[title for _, title in metrics],
        vertical_spacing=0.08
    )

    for row, (cols, _) in enumerate(metrics, start=1):

        # percentage of games where each player was first
        data = (
            firsts_df[cols]
            .eq(firsts_df[cols].min(axis=1), axis=0)
            .mean()
        )

        fig.add_trace(
            go.Pie(
                labels=[f"Rank {i}" for i in range(1, 5)],
                values=data.values,
                hole=0.4,
                marker_colors=[color_dict[i] for i in range(1, 5)],
                textinfo="percent",
                hovertemplate="%{label}<extra></extra>"
            ),
            row=row,
            col=1
        )

    fig.update_layout(
        height=500,
        margin=dict(t=40, l=0, r=20, b=50),
        showlegend=False,
        font=dict(
            family="Bahnschrift, Segoe UI, Arial"
        )
    )

    # style subplot titles
    fig.update_annotations(
        font_size=16,
        xanchor="left",
        x=0
    )
    for ann in fig['layout']['annotations']:
        ann['y'] += 0.01

    return fig

def plot_robbed(master_df, turns_df):
    timestamp_dict = (
        turns_df.groupby('game_id')['timestamp']
        .first()
        .to_dict()
    )
    #trim timestamps to just firt 10 characters for better display
    timestamp_dict = {game_id: timestamp[:10] for game_id, timestamp in timestamp_dict.items()}

    p2_lead_dict = p2_lead_pct(turns_df)
    robbed_df = master_df.pivot(
        index="game_id",
        columns="rank",
        values="stolen_from"
    )
    robbed_df['diff_1_2'] = robbed_df[1] - robbed_df[2]
    robbed_df['p2_lead_pct'] = robbed_df.index.map(p2_lead_dict)
    robbed_df['timestamp'] = robbed_df.index.map(timestamp_dict)
    pct_neg = (robbed_df['diff_1_2'] < 0).mean()
    pct_pos = (robbed_df['diff_1_2'] > 0).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=robbed_df['diff_1_2'],
        y=np.random.normal(0, 0.05, len(robbed_df)),  # jitter around 0,
        mode='markers',
        customdata=robbed_df[['timestamp']],
        marker=dict(color=robbed_df['p2_lead_pct'], colorscale=[
            [0.0, "#cbd5e1"],
            [1.0, "#0061FE"]
            ], 
            colorbar=dict(
                title=dict(text="Percent of Game<br>Runner-up Led",
                font=dict(size=14, family="Bahnschrift, Segoe UI, Arial")),
                tickformat=".0%", 
                thickness=35,
                len=1.1
                ),
            showscale=True),
            hovertemplate=("Game date: %{customdata[0]}<br>"
                "Difference in times robbed: %{x}<br>"
                "Runner-up led %{marker.color:.1%} of the game<extra></extra>")
    ))
    fig.update_layout(
        xaxis_title="Difference in Times Robbed (1st Place - 2nd Place)",
        yaxis=dict(
            visible=False,
            range=[-0.3, 0.3],
            showgrid=False,
            fixedrange=True,
            zeroline=False,
            automargin=False
        ),
        xaxis=dict(range=[-12,11], tickmode="array", \
                   tickvals=[-10, -5, 0, 5, 10], ticktext=['-10', '-5', '0', '5', '10'],
                   showgrid=False,
                   zeroline=True, zerolinewidth=1, zerolinecolor='lightgray', 
                   fixedrange=True),  
        height=350,
        margin=dict(t=20, l=0, r=20, b=50)
    )
    #annotations for left side
    fig.add_annotation(
        x=-11, y=-0.2,
        text=f"{pct_neg:.1%} of games",
        showarrow=False,
        font=dict(size=24, color="grey", family="Bahnschrift, Segoe UI, Arial"),
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="middle"
    )
    fig.add_annotation(
        x=-11, y=0.2,
        text="Runner-up robbed more",
        showarrow=False,
        font=dict(size=24, color="grey", family="Bahnschrift, Segoe UI, Arial"),
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="middle"
    )
    #annotations for right side
    fig.add_annotation(
        x=1, y=-0.2,
        text=f"{pct_pos:.1%} of games",
        showarrow=False,
        font=dict(size=24, color="grey", family="Bahnschrift, Segoe UI, Arial"),
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="middle"
    )
    fig.add_annotation(
        x=1, y=0.2,
        text="Winning player robbed more",
        showarrow=False,
        font=dict(size=24, color="grey", family="Bahnschrift, Segoe UI, Arial"),
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="middle"
    )
    #color different sides of y axis
    fig.add_vrect(
        x0=-1e9,
        x1=0,
        fillcolor=color_dict[2],
        opacity=0.15,
        line_width=0,
        layer="below"
    )
    fig.add_vrect(
        x0=0,
        x1=1e9,
        fillcolor=color_dict[1],
        opacity=0.15,
        line_width=0,
        layer="below"
    )
    return fig