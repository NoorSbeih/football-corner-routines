"""Run the warehouse SQL in order. Full rebuild from raw tables."""

from dataclasses import dataclass
from pathlib import Path

import duckdb

from corner_routines.config import ROOT, Pitch, database_path, get_pitch

SQL_FILES = (
    "staging/01_events.sql",
    "staging/02_corners.sql",
    "staging/03_sequences.sql",
    "marts/10_team_corners.sql",
    "marts/11_team_routines.sql",
    "marts/12_match_corners.sql",
)

SHOT_OUTCOMES = (
    "shot_first",
    "goal_first",
    "second_ball_shot",
    "second_ball_goal",
)


@dataclass(frozen=True)
class TransformSummary:
    corners: int
    short_n: int
    short_pct: float | None
    shot_n: int
    shot_pct: float | None
    first_shot_pct: float | None
    second_shot_n: int
    second_shot_pct: float | None
    goals: int
    top_routines: tuple[tuple[str, str, str, int, float], ...]


def apply_definitions(
    connection: duckdb.DuckDBPyConnection,
    pitch: Pitch,
    *,
    competition_key: str,
    competition_name: str,
) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS staging")
    connection.execute("CREATE SCHEMA IF NOT EXISTS marts")
    connection.execute(
        """
        CREATE OR REPLACE TABLE staging.meta AS
        SELECT ?::VARCHAR AS competition_key, ?::VARCHAR AS competition_name
        """,
        [competition_key, competition_name],
    )
    connection.execute(
        """
        CREATE OR REPLACE TABLE staging.definitions AS
        SELECT
            ?::DOUBLE AS pitch_length,
            ?::DOUBLE AS pitch_width,
            ?::DOUBLE AS box_x_min,
            ?::DOUBLE AS box_y_min,
            ?::DOUBLE AS box_y_max,
            ?::DOUBLE AS six_x_min,
            ?::DOUBLE AS six_y_min,
            ?::DOUBLE AS six_y_max,
            ?::DOUBLE AS mouth_y_min,
            ?::DOUBLE AS mouth_y_max,
            ?::DOUBLE AS corridor_y_min,
            ?::DOUBLE AS corridor_y_max,
            ?::DOUBLE AS short_max_distance,
            ?::DOUBLE AS cutoff_s,
            ?::DOUBLE AS left_y_min,
            ?::INTEGER AS min_routine_n,
            ?::INTEGER AS min_team_rank_n
        """,
        [
            pitch.length,
            pitch.width,
            pitch.box_x_min,
            pitch.box_y_min,
            pitch.box_y_max,
            pitch.six_x_min,
            pitch.six_y_min,
            pitch.six_y_max,
            pitch.mouth_y_min,
            pitch.mouth_y_max,
            pitch.corridor_y_min,
            pitch.corridor_y_max,
            pitch.short_max_distance,
            pitch.cutoff_s,
            pitch.left_y_min,
            pitch.min_routine_n,
            pitch.min_team_rank_n,
        ],
    )


def run_sql(connection: duckdb.DuckDBPyConnection, sql_root: Path) -> None:
    for relative in SQL_FILES:
        script = (sql_root / relative).read_text(encoding="utf-8")
        for statement in _statements(script):
            connection.execute(statement)


def transform(
    competition_key: str,
    competition_name: str,
    root: Path = ROOT,
    sql_root: Path | None = None,
) -> TransformSummary:
    if not competition_key.replace("_", "").isalnum():
        raise ValueError(f"unsafe competition key: {competition_key}")
    sql_dir = sql_root or (ROOT / "sql")
    database = database_path(root)
    connection = duckdb.connect(str(database))
    try:
        apply_definitions(
            connection,
            get_pitch(),
            competition_key=competition_key,
            competition_name=competition_name,
        )
        run_sql(connection, sql_dir)
        return _summarize(connection)
    finally:
        connection.close()


def format_summary(summary: TransformSummary) -> str:
    lines = [
        (
            f"corners: {summary.corners}  "
            f"short: {_fmt_pct(summary.short_pct)} ({summary.short_n})  "
            f"shot: {_fmt_pct(summary.shot_pct)} ({summary.shot_n})  "
            f"second ball: {_fmt_pct(summary.second_shot_pct)} ({summary.second_shot_n})  "
            f"goals: {summary.goals}"
        )
    ]
    if summary.shot_pct is not None and (summary.shot_pct > 50 or summary.shot_pct < 2):
        lines.append(
            "WARNING: tournament shot % is outside a believable range. "
            "Check the sequence cutoff and the first-contact rules before trusting the UI."
        )
    if summary.top_routines:
        lines.append("routines with n >= 8, by shot %:")
        for team, technique, zone, count, shot_pct in summary.top_routines:
            lines.append(f"  {team}: {technique} to {zone}, n={count}, shot {_fmt_pct(shot_pct)}")
    else:
        lines.append("no routine cell reached the minimum sample")
    return "\n".join(lines)


def _summarize(connection: duckdb.DuckDBPyConnection) -> TransformSummary:
    row = connection.execute(
        f"""
        SELECT
            count(*) AS corners,
            count(*) FILTER (WHERE is_short) AS short_n,
            100.0 * count(*) FILTER (WHERE is_short) / nullif(count(*), 0) AS short_pct,
            count(*) FILTER (WHERE outcome IN {SHOT_OUTCOMES}) AS shot_n,
            100.0 * count(*) FILTER (WHERE outcome IN {SHOT_OUTCOMES})
                / nullif(count(*), 0) AS shot_pct,
            100.0 * count(*) FILTER (WHERE outcome IN ('shot_first', 'goal_first'))
                / nullif(count(*), 0) AS first_shot_pct,
            count(*) FILTER (WHERE outcome IN ('second_ball_shot', 'second_ball_goal'))
                AS second_shot_n,
            100.0 * count(*) FILTER (WHERE outcome IN ('second_ball_shot', 'second_ball_goal'))
                / nullif(count(*), 0) AS second_shot_pct,
            coalesce(sum(goals), 0) AS goals
        FROM staging.corner_sequences
        """
    ).fetchone()
    routines = tuple(
        connection.execute(
            """
            SELECT team, technique, zone, n, shot_pct
            FROM marts.team_routines
            WHERE reliable
            ORDER BY shot_pct DESC, n DESC, team
            LIMIT 8
            """
        ).fetchall()
    )
    return TransformSummary(
        corners=int(row[0]),
        short_n=int(row[1]),
        short_pct=None if row[2] is None else float(row[2]),
        shot_n=int(row[3]),
        shot_pct=None if row[4] is None else float(row[4]),
        first_shot_pct=None if row[5] is None else float(row[5]),
        second_shot_n=int(row[6]),
        second_shot_pct=None if row[7] is None else float(row[7]),
        goals=int(row[8]),
        top_routines=tuple(
            (str(team), str(technique), str(zone), int(count), float(shot_pct))
            for team, technique, zone, count, shot_pct in routines
        ),
    )


def _statements(script: str) -> list[str]:
    chunks: list[str] = []
    buffer: list[str] = []
    for line in script.splitlines():
        buffer.append(line)
        if line.strip().endswith(";"):
            text = "\n".join(buffer).strip()
            if text.rstrip(";").strip():
                chunks.append(text)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        chunks.append(tail)
    return chunks


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"
