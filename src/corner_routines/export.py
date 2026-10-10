"""Write marts to the JSON files the static site reads."""

import json
from datetime import date, datetime
from numbers import Integral, Real
from pathlib import Path

import duckdb

from corner_routines.config import ROOT, database_path, get_competition, get_pitch, web_data_dir

SHOT_OUTCOMES = ("shot_first", "goal_first", "second_ball_shot", "second_ball_goal")


def export(competition_key: str, root: Path = ROOT) -> str:
    spec = get_competition(competition_key)
    pitch = get_pitch()
    folder = web_data_dir(root)
    connection = duckdb.connect(str(database_path(root)), read_only=True)
    try:
        teams = _rows(
            connection,
            """
            SELECT *
            FROM marts.team_corners
            ORDER BY rankable DESC, shot_pct DESC NULLS LAST, corners DESC, team
            """,
        )
        cells = _rows(
            connection,
            """
            SELECT *
            FROM marts.team_routines
            ORDER BY team, technique, zone
            """,
        )
        points = _rows(
            connection,
            """
            SELECT
                team_id, team, match_id, technique, first_contact_zone AS zone,
                outcome, shot, goals,
                end_x, end_y, first_contact_x, first_contact_y, side
            FROM marts.match_corners
            ORDER BY team_id, match_id, period, minute, second
            """,
        )
        catalog = _rows(
            connection,
            """
            SELECT
                m.match_id,
                m.match_date,
                m.competition_stage AS stage,
                m.home_team,
                m.away_team,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                count(c.corner_id) AS corners
            FROM raw.matches m
            LEFT JOIN marts.match_corners c ON c.match_id = m.match_id
            GROUP BY ALL
            ORDER BY corners DESC, m.match_id
            """,
        )
        sequences = _rows(
            connection,
            """
            SELECT *
            FROM marts.match_corners
            ORDER BY match_id, period, minute, second, index
            """,
        )
    finally:
        connection.close()

    default_match_id = int(catalog[0]["match_id"]) if catalog else None
    _dump(
        folder / "competitions.json",
        {
            "competitions": [
                {
                    "key": spec.key,
                    "name": spec.name,
                    "competition_id": spec.competition_id,
                    "season_id": spec.season_id,
                    "default_match_id": default_match_id,
                    "min_team_n": pitch.min_team_rank_n,
                    "min_routine_n": pitch.min_routine_n,
                }
            ]
        },
    )
    _dump(
        folder / "teams" / f"{spec.key}.json",
        {
            "competition": spec.key,
            "name": spec.name,
            "min_team_n": pitch.min_team_rank_n,
            "teams": teams,
        },
    )
    _dump(
        folder / "routines" / f"{spec.key}.json",
        {
            "competition": spec.key,
            "min_routine_n": pitch.min_routine_n,
            "cells": cells,
            "points": points,
        },
    )
    grouped: dict[int, list[dict]] = {}
    for row in sequences:
        grouped.setdefault(int(row["match_id"]), []).append(_tape_row(row))

    index = []
    matches_dir = folder / "matches"
    for match in catalog:
        match_id = int(match["match_id"])
        label = (
            f"{match['home_team']} {match['home_score']}-{match['away_score']} {match['away_team']}"
        )
        payload = {
            "match_id": match_id,
            "date": match["match_date"],
            "stage": match["stage"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "home_team_id": match["home_team_id"],
            "away_team_id": match["away_team_id"],
            "home_score": match["home_score"],
            "away_score": match["away_score"],
            "label": label,
            "corners": grouped.get(match_id, []),
        }
        _dump(matches_dir / f"{match_id}.json", payload)
        index.append(
            {
                "match_id": match_id,
                "date": match["match_date"],
                "stage": match["stage"],
                "label": label,
                "corners": int(match["corners"]),
                "home_team_id": match["home_team_id"],
                "away_team_id": match["away_team_id"],
            }
        )
    _dump(
        matches_dir / "index.json",
        {"default_match_id": default_match_id, "matches": index},
    )
    if default_match_id is None:
        return "none"
    featured = next(item for item in index if item["match_id"] == default_match_id)
    return f"{featured['label']} ({featured['corners']} corners)"


def _tape_row(row: dict) -> dict:
    return {
        "corner_id": row["corner_id"],
        "period": row["period"],
        "minute": row["minute"],
        "second": row["second"],
        "team": row["team"],
        "team_id": row["team_id"],
        "taker": row["taker"],
        "side": row["side"],
        "technique": row["technique"],
        "zone": row["first_contact_zone"],
        "outcome": row["outcome"],
        "xg": row["shot_xg"],
        "goals": row["goals"],
        "shot": row["shot"],
        "has_freeze_frame": row["has_freeze_frame"],
        "box_attackers": row["box_attackers"],
        "box_defenders": row["box_defenders"],
    }


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [
        {key: _clean(key, value) for key, value in zip(columns, row)} for row in cursor.fetchall()
    ]


def _clean(key: str, value: object) -> object:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        number = float(value)
        if "xg" in key:
            return round(number, 3)
        if key.endswith("_pct") or key == "shot_pct":
            return round(number, 1)
        if key.endswith("_x") or key.endswith("_y"):
            return round(number, 2)
        if key.startswith("median"):
            return round(number, 1)
        return round(number, 3)
    return value


def _dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
