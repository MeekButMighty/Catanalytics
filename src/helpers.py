import pandas as pd
import streamlit as st

def game_cropper(game_log):
    game = game_log.copy()
    for i, event in enumerate(game['events']):
        if "rolled" in event['text']:
            game['events'] = game['events'][i:]  # Slice from the first "rolled" event onward
            break
    return game

def count_dcs(player_name, turns):
    dc_count = 0
    for turn, events in turns.items():
        current_player = events[0].split()[0]
        if current_player == player_name:
            for event in events:
                if "bought [Development Card]" in event:
                    dc_count += 1
    return dc_count

def rank_players(row):
    players_ranked = []
    for player in row['playerSummary']:
        players_ranked.append(player['name'])
    return players_ranked

def get_place_order(row):
    placement_order = []
    for event in row['events']:
        if "placed a Settlement" in event['text']:
            player_name = event['text'].split()[0]
            if player_name not in placement_order:
                placement_order.append(player_name)
    return placement_order

def update_turns_df(game_id, turns_df, turns, player_columns, dc_dict):
    for turn, events in turns.items():
        last_row = turns_df.iloc[-1].copy()
        for player in player_columns.keys():
            vp_col, dc_col, settles_col, cities_col = player_columns[player]
            for event in events:
                if player+' built a Settlement' in event:
                    last_row[vp_col] += 1
                    last_row[settles_col] += 1
                    #print(f"Turn {turn}: {player} built a Settlement. +1 VP")
                elif player+' built a City' in event:
                    last_row[vp_col] += 1
                    last_row[cities_col] += 1
                    #print(f"Turn {turn}: {player} built a City. +1 VP")
                elif player+' received Longest Road' in event or player+' received Largest Army' in event:
                    last_row[vp_col] += 2
                    #print(f"Turn {turn}: {player} got Longest Road or Largest Army. +2 VP")
                elif player+" bought [Development Card]" in event:
                    last_row[dc_col] += 1
                    #assume vps drawn last
                    non_vp_dcs = dc_dict[player][0] - dc_dict[player][1]
                    if last_row[dc_col] > non_vp_dcs:
                        last_row[vp_col] += 1
                        #print(f"Turn {turn}: {player} bought a VP Development Card. +1 VP")
                elif "passed from "+player in event:
                     last_row[vp_col] -= 2
                     #print(f"Turn {turn}: {player} lost an award")
                elif "passed" in event and 'to '+player in event:
                     last_row[vp_col] += 2
                     #print(f"Turn {turn}: {player} lost an award")
        # Update turn number and game ID
        last_row['turn'] = turn
        last_row['gameid'] = game_id
            
        # Add updated row to the DataFrame
        turns_df.loc[len(turns_df)] = last_row
        
    return turns_df

def resource_counter(events, player, resource):
    count = 0
    for event in events:
        if player+" received starting" in event or player+" got" in event:
            count += event.count(resource)
    return count

def dc_counter(events, player):
    count = 0
    for event in events:
        if player+' bought [Development Card]' in event:
            count += 1
    return count

def robber_counter(events, player):
    if player == 'MadmanMeek':
        player = 'you'
    player = player.lower()
    stolen_from = 0
    stolen = 0
    for event in events:
        event_lower = event.lower()
        if 'from ' + player in event_lower:
            stolen_from += 1
        elif player in event_lower and 'stole' in event_lower:
            stolen += 1
    return stolen_from, stolen

def render_hex(label, value):
    st.markdown(f"""
    <div style="
        width: 190px;
        height: 190px;
        background: linear-gradient(145deg, #23272f, #14161a);
        clip-path: polygon(
            25% 6%, 75% 6%,
            100% 50%,
            75% 94%,
            25% 94%,
            0% 50%
        );
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        font-family: Bahnschrift;
        margin: auto;
        border: 1px solid #d4af37;
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.2);
    ">
        <div style="font-size: 48px; font-weight: 700; color: white;">
            {value}
        </div>
        <div style="font-size: 16px; color: #d4af37; letter-spacing: 0.5px;
        white-space: normal;
        text-align: center;
        word-wrap: break-word;
        overflow-wrap: break-word;
         max-width: 160px;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)

def kpi(master_df, turns_df):
    num_games = int(len(master_df)/4)
    meek_df = master_df[master_df['player'] == 'MadmanMeek'].copy()
    win_count= len(meek_df[meek_df['rank'] == 1])
    win_rate= (win_count/num_games)*100
    win_rate= f"{win_rate: .1f}%"
    avg_vps = meek_df['vp_total'].mean()
    avg_vps = f"{avg_vps: .2f}"
    num_turns = len(turns_df)
    total_players = len(master_df['player'].unique())
    return num_games, num_turns, total_players, win_rate, avg_vps

def time_dict(turns_df):
    timestamps = (
        turns_df["timestamp"]
        .drop_duplicates()
        .sort_values(ascending=False)
    )

    # create mapping:
    # pretty label -> raw timestamp
    timestamp_options = {
        pd.to_datetime(
            ts,
            format="%Y-%m-%d_%H-%M-%S"
        ).strftime("%B %d, %Y at %I:%M %p"): ts
        for ts in timestamps
    }
    return timestamp_options

def make_firsts_df(turns_df):
    columns = [
        "game_id",
        "p1_first_settle", "p1_first_city", "p1_first_dc",
        "p2_first_settle", "p2_first_city", "p2_first_dc",
        "p3_first_settle", "p3_first_city", "p3_first_dc",
        "p4_first_settle", "p4_first_city", "p4_first_dc"
    ]
    rows = []
    time_unit = "game_percentage"

    for game in turns_df["game_id"].unique():
        game_builds = turns_df[turns_df["game_id"] == game]
        new_row = {"game_id": game}

        for i in range(1, 5):
            settle_col = f"p{i}_settles"
            city_col = f"p{i}_cities"
            dc_col = f"p{i}_dcs"

            new_row[f"p{i}_first_settle"] = game_builds[game_builds[settle_col] > 2][time_unit].min()
            new_row[f"p{i}_first_city"] = game_builds[game_builds[city_col] > 0][time_unit].min()
            new_row[f"p{i}_first_dc"] = game_builds[game_builds[dc_col] > 0][time_unit].min()

        rows.append(new_row)

    return pd.DataFrame(rows, columns=columns)