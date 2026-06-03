from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import sqlite3
import pandas as pd
from pathlib import Path
from ingest import ingest_game


folder_path = "data/games"
db_path = "catan.db"


def backfill(folder_path):
    #get list of games already in table
    conn = sqlite3.connect(db_path)
    unique_ids = pd.read_sql("SELECT DISTINCT game_id FROM master", conn)['game_id'].tolist()
    #get list of file stems in folder
    file_stems = [f.stem for f in Path(folder_path).glob("*.json")]
    #find files that are not in db
    files_to_ingest = [stem for stem in file_stems if stem not in unique_ids]
    #if files to ingest, ingest them
    for file in files_to_ingest:
        ingest_game(f"{folder_path}/{file}.json")
        print(f"Backfilled {file}.json")
    conn.close()


class GameHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:
            return

        if not event.src_path.endswith(".json"):
            return

        print(f"New game detected: {event.src_path}")

        try:
            ingest_game(event.src_path)
            print("Successfully ingested")

        except Exception as e:
            print(f"Error ingesting {event.src_path}: {e}")

def start_watch():
    backfill(folder_path)
    observer = Observer()
    observer.schedule(
        GameHandler(),
        path=folder_path,
        recursive=False
    )

    observer.start()

    print(f"Watching {folder_path}...")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()