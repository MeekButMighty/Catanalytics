import json
import pandas as pd
from pathlib import Path

def load_all_games(path="data/games"):
    all_games = []

    for file in Path(path).glob("*.json"):
        with open(file) as f:
            game = json.load(f)

        df = pd.json_normalize(game)
        df["game_id"] = file.stem
        all_games.append(df)

    return pd.concat(all_games, ignore_index=True)