import pandas as pd
from src.helpers import game_cropper, count_dcs, rank_players, update_turns_df
from src.helpers import get_place_order, resource_counter, dc_counter, robber_counter
from src.helpers import count_discards, count_trades


def make_placement_df(df):
    columns = ['placement_order', 'rank_1', 'rank_2', 'rank_3', 'rank_4']
    placement_df = pd.DataFrame(columns=columns)
    for _, row in df.iterrows():
        # Create list of players ranked
        players_ranked = rank_players(row)
        
        # Create list of players in placement order
        placement_order = []
        for event in row['events']:
            if "placed a Settlement" in event['text']:
                player_name = event['text'].split()[0]
                if player_name not in placement_order:
                    placement_order.append(player_name)
        
        # Name placement order
        placements = ['1_8', '2_7', '3_6', '4_5']
        
        # Add to placement dataframe
        for player in placement_order:
            placement_idx = placement_order.index(player)
            entry = {
                "placement_order": placements[placement_idx],
                "rank_1": 1 if players_ranked.index(player) == 0 else 0,
                "rank_2": 1 if players_ranked.index(player) == 1 else 0,
                "rank_3": 1 if players_ranked.index(player) == 2 else 0,
                "rank_4": 1 if players_ranked.index(player) == 3 else 0
            }
            placement_df = pd.concat([placement_df, pd.DataFrame([entry])], ignore_index=True)  # Use `entry` instead of `row`
    placement_df = placement_df.groupby('placement_order').sum().reset_index()
    placement_df = placement_df.iloc[::-1].reset_index(drop=True)
    placement_df[['rank_1', 'rank_2', 'rank_3', 'rank_4']] = placement_df[['rank_1', 'rank_2', 'rank_3', 'rank_4']] / placement_df[['rank_1', 'rank_2', 'rank_3', 'rank_4']].sum(axis=1).values.reshape(-1, 1)
    return placement_df

def make_master_df(df):
    columns = ["game_id","player", "rank", "placement_order",
           "vp_total", "vp_settle", "vp_city", "vp_dc",
           "longest_road", "largest_army", "dcs_purchased",
           "Brick", "Grain", "Ore", "Lumber", "Wool",
           "stolen_from", 'stole', 'times_discarded', 'cards_discarded',
           'tot_trades', 'trades_init', 'trades_accep',
           'margin', 'spread']

    master_df = pd.DataFrame(columns= columns)
    for _, row in df.iterrows():
        # Create list of players ranked
        game_id = row['game_id']
        players_ranked = rank_players(row)
        place_order = get_place_order(row)
        scores = [plr["victoryPoints"] for plr in row["playerSummary"]]
        margin = scores[0]-scores[1]
        spread = scores[0]-scores[3]
        events = [event["text"] for event in row["events"]]
        for player in players_ranked:
            summ_stats = next(
                (p for p in row["playerSummary"] if p["name"] == player))
            tot_trades, trades_init, trades_accep = count_trades(events, player)
            new_row = {
                "game_id": game_id,
                "player": player,
                "rank": players_ranked.index(player) + 1,
                "placement_order": place_order.index(player) + 1,
                "vp_total": int(summ_stats['victoryPoints']),
                "vp_settle": int(summ_stats['settlements']),
                'vp_city': int(summ_stats['cities']),
                "vp_dc": int(summ_stats.get('vp_breakdown', 0) or 0),
                "longest_road": int(summ_stats.get('longest_road', 0) or 0), 
                "largest_army": int(summ_stats.get('largest_army', 0) or 0),
                "dcs_purchased": dc_counter(events, player),
                "Brick": resource_counter(events, player, 'Brick'), 
                "Grain": resource_counter(events, player, 'Grain'), 
                "Ore": resource_counter(events, player, 'Ore'), 
                "Lumber": resource_counter(events, player, 'Lumber'), 
                "Wool":resource_counter(events, player, 'Wool'),
                "stolen_from": robber_counter(events, player)[0],
                "stole": robber_counter(events, player)[1],
                "times_discarded": count_discards(events, player)[1],
                "cards_discarded": count_discards(events, player)[0],
                "tot_trades": tot_trades,
                "trades_init": trades_init,
                "trades_accep": trades_accep,
                "margin": margin,
                "spread": spread
            }
            master_df.loc[len(master_df)] = new_row

    return master_df

def make_turns_df(df):
    columns = ["game_id", "timestamp", "turn", 
           "p1_vps", "p1_dcs", "p1_settles", "p1_cities",
           "p2_vps", "p2_dcs", "p2_settles", "p2_cities",
           "p3_vps", "p3_dcs", "p3_settles", "p3_cities",
           "p4_vps", "p4_dcs", "p4_settles", "p4_cities"]
    turns_df = pd.DataFrame(columns=columns)
    for _, row in df.iterrows():
        # Create list of players ranked
        game_id = row['game_id']
        timestamp= row['timestamp']
        players_ranked = rank_players(row)
        cropped_game = game_cropper(row)
        events_text = [event["text"] for event in cropped_game["events"]]
        events = cropped_game['events']
        turns = {}
        current_turn = 1
        turns[current_turn] = []
        for event in events:
            if 'won' in event['text']:
                break
            if "<hr>" in event['html']:
                current_turn += 1
                turns[current_turn] = []
            else:
                turns[current_turn].append(event['text'])
        # Remove empty turns
        turns = {turn: events for turn, events in turns.items() if events}
        #create dict for dev card info
        dc_dict = {}
        for player in players_ranked:
            dc_dict[player] = [dc_counter(events_text, player)]
        for item in row['playerSummary']:
            player = item['name']
            vps = item.get('vp_breakdown', 0)
            dc_dict[player].append(int(vps))
        new_row = {
            "game_id": game_id,
            "timestamp": timestamp,
            "turn": 0,
            "p1_vps": 2, "p1_dcs": 0, "p1_settles": 2, "p1_cities": 0,
            "p2_vps": 2, "p2_dcs": 0, "p2_settles": 2, "p2_cities": 0,
            "p3_vps": 2, "p3_dcs": 0, "p3_settles": 2, "p3_cities": 0,
            "p4_vps": 2, "p4_dcs": 0, "p4_settles": 2, "p4_cities": 0
        }
        turns_df = pd.concat([turns_df, pd.DataFrame([new_row])], ignore_index=True)
        # Create dictionary for mapping player names to dataframe columns
        player_columns = {}
        for i, player in enumerate(players_ranked, start=1):
            player_columns[player] = (f'p{i}_vps', f'p{i}_dcs', f'p{i}_settles', f'p{i}_cities')
        # Update the dataframe with the turns from game
        update_turns_df(game_id, turns_df, turns, player_columns, dc_dict)
        # Add percentage completed column
        turns_df['game_percentage'] = turns_df['turn'] / turns_df.groupby('game_id')['turn'].transform('max')
        turns_df['percentage_bin'] = (turns_df['game_percentage'] // 0.05) * 0.05
        # Correct final scores to be in 1.0 percentage bin
        turns_df.loc[turns_df['game_percentage'] == 1.0, 'percentage_bin'] = 1.0

    return turns_df      

def make_avg_prog_df(df):
    average_vps = df.groupby('percentage_bin')[['p1_vps', 'p2_vps', 'p3_vps', 'p4_vps']].mean().reset_index()
    return average_vps

