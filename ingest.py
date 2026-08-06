import sqlite3
import json
from pathlib import Path
import pandas as pd
#import importlib
#import src.transforms
#importlib.reload(src.transforms)
from src.transforms import make_master_df, make_turns_df, make_checkpt_df

DB_PATH = "catan.db"

def ingest_game(file):
    conn = sqlite3.connect(DB_PATH)

    with open(file, 'r') as f:
        game_data = json.load(f)
    game_id = Path(file).stem

    #normalize json
    df = pd.json_normalize(game_data)
    df["game_id"] = game_id
    
    #create dfs
    master = make_master_df(df)
    turns = make_turns_df(df)
    checkpt = make_checkpt_df(turns, [3, 5, 7, 9])

    #insert master and turns into db
    master.to_sql('master', conn, if_exists='append', index=False)
    #print(f"Inserted {game_id} master data into master table.")
    turns.to_sql('turns', conn, if_exists='append', index=False)
    #print(f"Inserted {game_id} turns data into turns table.")
    checkpt.to_sql('checkpoints', conn, if_exists='append', index=False)
    #print(f"Inserted {game_id} checkpoint data into checkpoints table.")

    #finish
    conn.commit()
    conn.close()
    #print(f"Finished ingesting {game_id}.")