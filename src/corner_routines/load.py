"""Load the parquet cache into DuckDB raw tables. Full rebuild, no HTTP."""

from dataclasses import dataclass
from pathlib import Path

import duckdb

from corner_routines.config import database_path, events_dir, frames_dir, matches_path

FRAME_SCHEMA = """
    match_id BIGINT,
    id VARCHAR,
    teammate BOOLEAN,
    actor BOOLEAN,
    keeper BOOLEAN,
    x DOUBLE,
    y DOUBLE
"""


@dataclass(frozen=True)
class LoadResult:
    match_count: int
    event_count: int
    matches_with_360: int
    frame_rows: int
    database: Path


def load_raw(competition_key: str, root: Path) -> LoadResult:
    matches_file = matches_path(root, competition_key)
    event_folder = events_dir(root, competition_key)
    frame_folder = frames_dir(root, competition_key)
    if not matches_file.exists():
        raise FileNotFoundError(f"missing matches cache: {matches_file}")
    event_files = sorted(event_folder.glob("*.parquet"))
    if not event_files:
        raise FileNotFoundError(f"missing event cache: {event_folder}")

    database = database_path(root)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database))
    try:
        connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
        matches_sql = _sql_path(matches_file)
        events_sql = _sql_path(event_folder / "*.parquet")
        connection.execute(
            f"CREATE OR REPLACE TABLE raw.matches AS SELECT * FROM read_parquet('{matches_sql}')"
        )
        connection.execute(
            "CREATE OR REPLACE TABLE raw.events AS "
            f"SELECT * FROM read_parquet('{events_sql}', union_by_name=true)"
        )
        frame_files = sorted(frame_folder.glob("*.parquet"))
        if frame_files:
            frames_sql = _sql_path(frame_folder / "*.parquet")
            connection.execute(
                "CREATE OR REPLACE TABLE raw.freeze_frames AS "
                f"SELECT * FROM read_parquet('{frames_sql}', union_by_name=true)"
            )
        else:
            connection.execute(f"CREATE OR REPLACE TABLE raw.freeze_frames ({FRAME_SCHEMA})")
        match_count = connection.execute("SELECT count(*) FROM raw.matches").fetchone()[0]
        event_count = connection.execute("SELECT count(*) FROM raw.events").fetchone()[0]
        frame_rows = connection.execute("SELECT count(*) FROM raw.freeze_frames").fetchone()[0]
        with_360 = connection.execute(
            "SELECT count(DISTINCT match_id) FROM raw.freeze_frames"
        ).fetchone()[0]
    finally:
        connection.close()
    return LoadResult(
        match_count=int(match_count),
        event_count=int(event_count),
        matches_with_360=int(with_360),
        frame_rows=int(frame_rows),
        database=database,
    )


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")
