import sqlite3
import json
from pathlib import Path
import pandas as pd
#import importlib
#import src.transforms
#importlib.reload(src.transforms)
from src.transforms import make_master_df, make_turns_df

DB_PATH = "catan.db"

def ingest_game(file):
    conn = sqlite3.connect(DB_PATH)

    with open(file, 'r') as f:
        game_data = json.load(f)
    game_id = Path(file).stem

    #insert raw json into db
    conn.execute(
        """
        INSERT OR IGNORE INTO games (game_id, raw_json)
        VALUES (?, ?)
        """,
        (game_id, json.dumps(game_data))
    )
    #print(f"Inserted {game_id} JSON into games.")

    #normalize json
    df = pd.json_normalize(game_data)
    df["game_id"] = game_id
    
    #create dfs
    master = make_master_df(df)
    turns = make_turns_df(df)

    #insert master and turns into db
    master.to_sql('master', conn, if_exists='append', index=False)
    #print(f"Inserted {game_id} master data into master table.")
    turns.to_sql('turns', conn, if_exists='append', index=False)
    #print(f"Inserted {game_id} turns data into turns table.")

    #finish
    conn.commit()
    conn.close()
    #print(f"Finished ingesting {game_id}.")
