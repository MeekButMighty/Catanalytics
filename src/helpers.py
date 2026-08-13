import pandas as pd
import streamlit as st
import base64
from pathlib import Path
from itertools import product

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
                elif "passed from "+player in event or ("lost" in event and player in event):
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
        if 'from ' + player in event_lower and 'stole' in event_lower:
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

def p2_lead_pct(turns_df):
    vp_cols = ['p1_vps', 'p2_vps', 'p3_vps', 'p4_vps']
    p2_lead_dict = {}
    for game_id in turns_df['game_id'].unique():
        game_turns = turns_df[turns_df['game_id'] == game_id]
        num_turns = len(game_turns)
        p2_lead_turns = game_turns['p2_vps'] == game_turns[vp_cols].max(axis=1)
        p2_lead_pct = p2_lead_turns.sum() / num_turns
        p2_lead_dict[game_id] = p2_lead_pct
    return p2_lead_dict

def count_discards(events, player):
    count = 0
    cards = 0
    for event in events:
        if player+" discarded" in event:
            discarded = event.count('[')
            cards += discarded
            count += 1
    return cards, count

def count_trades(events, player):
    trades = 0
    trades_init = 0
    trades_accep = 0
    for event in events:
        if player+" gave" in event and "bank" not in event:
            trades += 1
            trades_init += 1
        if "from "+player in event and "gave" in event:
            trades += 1
            trades_accep += 1
    return trades, trades_init, trades_accep

def count_actions(events, player, action):
    count = 0
    if action == 'road':
        for event in events:
            if player +  ' built a Road' in event:
                count += 1
    elif action == 'dc':
        for event in events:
            if player + ' bought [Development Card]' in event:
                count += 1
    return count

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

def port_solver(inputs, output):
    """solves tough port trades

    Args:
        inputs (dictionary): keys are resources, values are how many of each resource were given to the bank. 
        ex: {'Grain': 0, 'Ore': 3, 'Wool': 2, 'Brick': 0, 'Lumber': 0}
        output (int): how many resources were received in return.
    
    Returns: 
        dictionary with type of port as keys and how many times each port was used as values. If no valid combination is found, returns an empty dictionary.
    """

    resources = ['Grain', 'Ore', 'Wool', 'Brick', 'Lumber']
    port_dict = {resource: 0 for resource in resources}
    port_dict['3:1'] = 0

    possible_ports = [2,3,4]
    nonzero_inputs = [i for i in inputs.values() if i > 0]

    num_ports = len(nonzero_inputs)
    combinations = list(product(possible_ports, repeat=num_ports))

    valid_combinations = []

    for combo in combinations:
        all_trades = 0
        for i, input in enumerate(nonzero_inputs):
            trade = input / combo[i]
            #if trade is not an integer, skip this combination
            if trade != int(trade):
                break
            all_trades += trade
        if all_trades == output:
            valid_combinations.append(combo)

    #if there is only one valid combination, use it
    if len(valid_combinations) == 1:
        valid_combo = valid_combinations[0]
        nonzero_items = [(k, v) for k, v in inputs.items() if v > 0]
        for i, (resource, count) in enumerate(nonzero_items):
            if valid_combo[i] == 3:
                port_dict['3:1'] += count // valid_combo[i]
            elif valid_combo[i] == 2:
                port_dict[resource] = count // valid_combo[i]
        return port_dict

def count_port_usage(events, player):
    """
    Count how many times a player used a specific port.

    Parameters:
        events (list[str]): Trade event strings
        player (str): Username
        port (str): Port type ("3:1", "grain", "ore", etc.)

    Returns:
        dict: A dictionary with port types as keys and their usage counts as values.
    """
    resources = ['Grain', 'Ore', 'Wool', 'Brick', 'Lumber']

    port_dict = {resource: 0 for resource in resources}
    port_dict['3:1'] = 0  # Add a key for the 3:1 port

    for event in events:
        if not event.startswith(player+ ' gave bank'):
            continue

        #track resources given and received
        start = event.find("gave bank")
        end = event.find("and took")
        given_text = event[start:end]
        received_text = event[end:]
        num_received = received_text.count('[') 
        num_given = given_text.count('[')
        given = {}
        for resource in resources:
            given[resource]= given_text.count(resource)

        #if only one type of resource was given, then counting is simple
        if sum(value != 0 for value in given.values()) == 1:
            resource_given = next((resource for resource, count in given.items() if count > 0), None)
            ratio = num_given / num_received
            if ratio == 3:
                times_used = num_given // 3
                port_dict['3:1'] += times_used
            elif ratio == 2:
                times_used = num_given // 2
                port_dict[resource_given] += times_used
        #otherwise, need more logic to determine which ports were used
        else:
            complex_trade = port_solver(given, num_received)
            #if complex trade is null
            if not complex_trade:
                #trade not solveable with available data, skip
                continue
            for resource, count in complex_trade.items():
                port_dict[resource] += count

    return port_dict

def load_svg(path, color):
    svg = Path(path).read_text()
    svg = svg.replace("#000000", color)
    if path == "assets/grain.svg":
        svg = svg.replace("<path ", f'<path fill="{color}" ')

    return (
        "data:image/svg+xml;base64,"
        + base64.b64encode(svg.encode()).decode()
    )