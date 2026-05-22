import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

color_dict = {
    1: '#D4AF37',  # Gold
    2: '#B0B7C0',  # Silver
    3: '#B87333',  # Bronze
    4: '#3c78d8'   # Rose
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

    summary["value"] = summary["count"] / summary.groupby("placement_order")["count"].transform("sum")

    plot_df = summary.pivot(
        index="placement_order",
        columns="rank",
        values="value"
    ).fillna(0)
    # make sure ordering is clean
    plot_df = plot_df.sort_index()

    fig, ax = plt.subplots(figsize=(8, 5))

    left = [0] * len(plot_df)

    for rank in plot_df.columns:
        ax.barh(
            plot_df.index,
            plot_df[rank],
            left=left,
            label=f"Rank {rank}",
            color=color_dict[rank]
        )
        left = [l + v for l, v in zip(left, plot_df[rank])]

    #ax.set_xlabel("Proportion of Games")
    #ax.set_title("Placement Order Distribution by Rank")
    ax.set_xlim(0,1)
    ax.invert_yaxis()

    #change axis labels to be more descriptive
    ax.set_yticks([4,3,2,1])
    ax.set_yticklabels(['4th, 5th', '3rd, 6th', '2nd, 7th', '1st, 8th'])
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])

    #text and labels
    plt.text(-0.11, 0, "Does Placement Order Affect Game Outcome?", ha='left', va='center', fontsize=18, fontweight='bold')
    plt.text(-0.11, 0.3, "Proportion of games ended in", ha='left', va='center', fontsize=12)
    plt.text(0.294, 0.3, "1st,", ha='left', va='center', fontsize=12, color=color_dict[1], fontweight='bold')
    plt.text(0.357, 0.3, "2nd,", ha='left', va='center', fontsize=12, color=color_dict[2], fontweight='bold')
    plt.text(0.43, 0.3, "3rd,", ha='left', va='center', fontsize=12, color=color_dict[3], fontweight='bold')
    plt.text(0.5, 0.3, "and", ha='left', va='center', fontsize=12)
    plt.text(0.56, 0.3, "4th", ha='left', va='center', fontsize=12, color=color_dict[4], fontweight='bold')
    plt.text(0.618, 0.3, "place", ha='left', va='center', fontsize=12)
    sns.despine(left=True)
    
    return fig

def plot_firsts(turns_df, num_players):
    columns = ["game_id", "p1_first_settle", "p1_first_city", "p1_first_dc",
           "p2_first_settle", "p2_first_city", "p2_first_dc",
           "p3_first_settle", "p3_first_city", "p3_first_dc",
           "p4_first_settle", "p4_first_city", "p4_first_dc"]
    first_df = pd.DataFrame(columns=columns)
    time_unit = 'game_percentage'  # Change to 'turn' if you want to use turn number instead of percentage
    for game in turns_df['game_id'].unique():
            game_builds = turns_df[turns_df['game_id'] == game]
            new_row = {"game_id": game}
            for i in range(1, 5):
                settle_col = f'p{i}_settles'
                city_col = f'p{i}_cities'
                dc_col = f'p{i}_dcs'
                #for each game, find turn number of first settlement, city, and dev card for each player
                new_row[f'p{i}_first_settle'] = game_builds[game_builds[settle_col] > 2][f'{time_unit}'].min()
                new_row[f'p{i}_first_city'] = game_builds[game_builds[city_col] > 0][f'{time_unit}'].min()
                new_row[f'p{i}_first_dc'] = game_builds[game_builds[dc_col] > 0][f'{time_unit}'].min()
            first_df = pd.concat([first_df, pd.DataFrame([new_row])], ignore_index=True)
    #restructure data

    settle_cols = [c for c in first_df.columns if "first_settle" in c]
    settle_cols = settle_cols[:num_players]
    settle_long = first_df.melt(
        id_vars="game_id",
        value_vars=settle_cols,
        var_name="player",
        value_name="turn"
    ).dropna()
    settle_long["player"] = settle_long["player"].str.extract(r"p(\d)")[0].astype(int)

    city_cols = [c for c in first_df.columns if "first_city" in c]
    city_cols = city_cols[:num_players]
    city_long = first_df.melt(
        id_vars="game_id",
        value_vars=city_cols,
        var_name="player",
        value_name="turn"
    ).dropna()
    city_long["player"] = city_long["player"].str.extract(r"p(\d)")[0].astype(int)

    dc_cols = [c for c in first_df.columns if "first_dc" in c]
    dc_cols = dc_cols[:num_players]
    dc_long = first_df.melt(
        id_vars="game_id",
        value_vars=dc_cols,
        var_name="player",
        value_name="turn"
    ).dropna()
    dc_long["player"] = dc_long["player"].str.extract(r"p(\d)")[0].astype(int)

    #now, we plot
    sns.set_theme(style="whitegrid")

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(10, 6),
        sharex=True
    )

    # -------------------------
    # A) First Settlement
    # -------------------------
    sns.kdeplot(
        data=settle_long,
        x="turn",
        hue="player",
        fill=True,
        common_norm=False,
        bw_adjust=0.8,
        palette=color_dict,
        ax=axes[0]
    )

    axes[0].set_title("First Settlement Built")
    #axes[0].grid(False)

    # -------------------------
    # B) First City
    # -------------------------
    sns.kdeplot(
        data=city_long,
        x="turn",
        hue="player",
        fill=True,
        common_norm=False,
        bw_adjust=0.8,
        palette=color_dict,
        ax=axes[1]
    )

    axes[1].set_title("First City Built")
    #axes[1].grid(False)

    # -------------------------
    # C) First Dev Card
    # -------------------------
    sns.kdeplot(
        data=dc_long,
        x="turn",
        hue="player",
        fill=True,
        common_norm=False,
        bw_adjust=0.8,
        palette=color_dict,
        ax=axes[2]
    )

    axes[2].set_title("First Dev Card Drawn")
    #axes[2].grid(False)
    axes[2].set_xlabel("Percentage of Game Completed")
    axes[2].set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    axes[2].set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    axes[2].tick_params(axis='x', bottom=True)

    for axis in axes:
         axis.set_xlim(0,1)
         axis.set_ylabel("")
         axis.grid(False)
         axis.tick_params(axis='y', left=True)
         axis.grid(axis='x', alpha=0.9)
         legend = axis.get_legend()
         if legend:
                legend.remove()

    plt.text(x=0, y=3.99, s="A Dev Card too early could cost you the game", 
            ha='left', va='center', transform=axes[2].transAxes,
            fontsize=25, fontweight='bold')
    plt.text(x=0, y=3.75, s="Action distributions for", ha='left', va='center', transform=axes[2].transAxes, fontsize=17)
    plt.text(x=0.31, y=3.75, s="winning player", ha='left', va='center', transform=axes[2].transAxes, fontsize=17, fontweight='bold', color=color_dict[1])
    plt.text(x=0.53, y=3.75, s="and", ha='left', va='center', transform=axes[2].transAxes, fontsize=17)
    plt.text(x=0.59, y=3.75, s="runner-up", ha='left', va='center', transform=axes[2].transAxes, fontsize=17, fontweight='bold', color=color_dict[2])
    plt.text(x=-0.07, y=3.55, s="Density", ha='left', va='center', transform=axes[2].transAxes, fontsize=11.5)

    plt.close(fig)
    
    return fig

def plot_avg_prog(df):
    fig = plt.figure(figsize=(10, 6))
    plt.plot(df['percentage_bin'], df['p1_vps'], label='Player 1')
    plt.plot(df['percentage_bin'], df['p2_vps'], label='Player 2')
    plt.plot(df['percentage_bin'], df['p3_vps'], label='Player 3')
    plt.plot(df['percentage_bin'], df['p4_vps'],  label='Player 4')
    plt.xlabel('Percentage of Game Completed')
    plt.ylabel('Average Victory Points')
    plt.title('Average Victory Points Progression Over Game Percentage')
    plt.legend()
    sns.despine()

    return fig

