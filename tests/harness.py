"""Build a tiny warehouse from hand-written events. No network."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from corner_routines.config import ROOT, get_pitch
from corner_routines.transform import apply_definitions, run_sql

SQL_ROOT = ROOT / "sql"
PITCH = get_pitch()


def loc(x: float, y: float) -> str:
    return json.dumps([round(x, 4), round(y, 4)])


def stamp(total_s: float) -> str:
    minute = int(total_s // 60)
    second = total_s - minute * 60
    return f"00:{minute:02d}:{second:06.3f}"


def flipped(x: float, y: float) -> str:
    """Location as the defending team would store it."""
    return loc(PITCH.length - x, PITCH.width - y)


def event(**overrides: object) -> dict:
    base: dict[str, object] = {
        "id": "e",
        "match_id": 1,
        "period": 1,
        "index": 1,
        "timestamp": stamp(0),
        "minute": 0,
        "second": 0,
        "type": "Pass",
        "team": "Attack",
        "team_id": 1,
        "player": "Taker",
        "player_id": 10,
        "pass_type": None,
        "pass_outcome": None,
        "pass_technique": None,
        "location": loc(60, 40),
        "pass_end_location": None,
        "shot_outcome": None,
        "shot_statsbomb_xg": None,
        "shot_type": None,
        "goalkeeper_type": None,
    }
    base.update(overrides)
    total = overrides.get("total_s")
    if isinstance(total, (int, float)):
        base["timestamp"] = stamp(float(total))
        base["minute"] = int(float(total) // 60)
        base["second"] = int(float(total) % 60)
    base.pop("total_s", None)
    return base


def corner(
    *,
    event_id: str = "c1",
    index: int = 1,
    total_s: float = 10,
    side: str = "right",
    technique: str | None = "Inswinging",
    end: tuple[float, float] = (110, 40),
    complete: bool = False,
    team: str = "Attack",
    team_id: int = 1,
    match_id: int = 1,
    period: int = 1,
) -> dict:
    start_y = PITCH.width if side == "left" else 0.0
    return event(
        id=event_id,
        match_id=match_id,
        period=period,
        index=index,
        total_s=total_s,
        type="Pass",
        team=team,
        team_id=team_id,
        player="Taker",
        player_id=10,
        pass_type="Corner",
        pass_technique=technique,
        pass_outcome=None if complete else "Incomplete",
        location=loc(PITCH.length, start_y),
        pass_end_location=loc(*end),
    )


def warehouse(
    events: list[dict],
    frames: list[dict] | None = None,
) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.execute("CREATE SCHEMA raw")
    frame = pd.DataFrame(events)
    for column in (
        "id",
        "timestamp",
        "type",
        "team",
        "player",
        "pass_type",
        "pass_outcome",
        "pass_technique",
        "location",
        "pass_end_location",
        "shot_outcome",
        "shot_type",
        "goalkeeper_type",
    ):
        frame[column] = frame[column].astype("string")
    connection.register("events_df", frame)
    connection.execute(
        """
        CREATE TABLE raw.events AS
        SELECT
            id::VARCHAR AS id,
            try_cast(match_id AS BIGINT) AS match_id,
            try_cast(period AS INTEGER) AS period,
            try_cast(index AS INTEGER) AS index,
            timestamp::VARCHAR AS timestamp,
            try_cast(minute AS INTEGER) AS minute,
            try_cast(second AS INTEGER) AS second,
            type::VARCHAR AS type,
            team::VARCHAR AS team,
            try_cast(team_id AS BIGINT) AS team_id,
            player::VARCHAR AS player,
            try_cast(player_id AS BIGINT) AS player_id,
            pass_type::VARCHAR AS pass_type,
            pass_outcome::VARCHAR AS pass_outcome,
            pass_technique::VARCHAR AS pass_technique,
            location::VARCHAR AS location,
            pass_end_location::VARCHAR AS pass_end_location,
            shot_outcome::VARCHAR AS shot_outcome,
            try_cast(shot_statsbomb_xg AS DOUBLE) AS shot_statsbomb_xg,
            shot_type::VARCHAR AS shot_type,
            goalkeeper_type::VARCHAR AS goalkeeper_type
        FROM events_df
        """
    )
    if frames:
        connection.register("frames_df", pd.DataFrame(frames))
        connection.execute(
            """
            CREATE TABLE raw.freeze_frames AS
            SELECT
                try_cast(match_id AS BIGINT) AS match_id,
                id::VARCHAR AS id,
                teammate::BOOLEAN AS teammate,
                coalesce(actor, false)::BOOLEAN AS actor,
                coalesce(keeper, false)::BOOLEAN AS keeper,
                try_cast(x AS DOUBLE) AS x,
                try_cast(y AS DOUBLE) AS y
            FROM frames_df
            """
        )
    else:
        connection.execute(
            """
            CREATE TABLE raw.freeze_frames (
                match_id BIGINT,
                id VARCHAR,
                teammate BOOLEAN,
                actor BOOLEAN,
                keeper BOOLEAN,
                x DOUBLE,
                y DOUBLE
            )
            """
        )
    apply_definitions(
        connection,
        PITCH,
        competition_key="test",
        competition_name="Test",
    )
    run_sql(connection, SQL_ROOT)
    return connection


def sequences(connection: duckdb.DuckDBPyConnection) -> list[tuple]:
    return connection.execute(
        """
        SELECT
            corner_id, technique, is_short, first_contact_zone, outcome,
            shot_xg, goals, has_freeze_frame, box_attackers, box_defenders
        FROM staging.corner_sequences
        ORDER BY period, index
        """
    ).fetchall()


def repo_root() -> Path:
    return ROOT
