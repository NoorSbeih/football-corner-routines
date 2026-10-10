"""Prefect flow: extract, load, transform, export."""

from pathlib import Path

from prefect import flow, task

from corner_routines.config import ROOT, ConfigError, get_competition
from corner_routines.export import export
from corner_routines.extract import extract_competition
from corner_routines.load import load_raw
from corner_routines.transform import format_summary, transform


@task(name="extract")
def extract_task(competition_key: str, competition_id: int, season_id: int) -> dict:
    result = extract_competition(
        competition_key=competition_key,
        competition_id=competition_id,
        season_id=season_id,
        root=ROOT,
    )
    return {
        "match_count": result.match_count,
        "matches_http": result.matches_http,
        "event_http_fetches": result.event_http_fetches,
        "frame_http_fetches": result.frame_http_fetches,
        "matches_with_360": result.matches_with_360,
        "from_cache": result.from_cache,
    }


@task(name="load")
def load_task(competition_key: str) -> dict:
    result = load_raw(competition_key, ROOT)
    try:
        relative = result.database.relative_to(ROOT)
    except ValueError:
        relative = result.database
    return {
        "match_count": result.match_count,
        "event_count": result.event_count,
        "matches_with_360": result.matches_with_360,
        "frame_rows": result.frame_rows,
        "database": Path(relative).as_posix(),
    }


@task(name="transform")
def transform_task(competition_key: str, competition_name: str) -> dict:
    summary = transform(competition_key, competition_name, ROOT)
    print(format_summary(summary))
    return {
        "corners": summary.corners,
        "shot_pct": summary.shot_pct,
        "second_shot_pct": summary.second_shot_pct,
    }


@task(name="export")
def export_task(competition_key: str) -> str:
    return export(competition_key, ROOT)


@flow(name="corner-routines-build")
def build_flow(competition: str = "wc2022") -> None:
    try:
        spec = get_competition(competition)
    except ConfigError as exc:
        raise SystemExit(str(exc)) from exc
    extracted = extract_task(spec.key, spec.competition_id, spec.season_id)
    loaded = load_task(spec.key)
    cache = "cache hit, skipped HTTP" if extracted["from_cache"] else "fetched from StatsBomb"
    print(
        f"competition: {spec.key} ({spec.name}, id {spec.competition_id}, season {spec.season_id})"
    )
    print(
        f"extract: {cache}, {extracted['match_count']} matches, "
        f"{extracted['event_http_fetches']} event HTTP requests, "
        f"{extracted['frame_http_fetches']} frame HTTP requests"
    )
    print(f"raw.matches: {loaded['match_count']}")
    print(f"raw.events: {loaded['event_count']}")
    print(
        f"raw.freeze_frames: {loaded['frame_rows']} players "
        f"across {loaded['matches_with_360']} matches"
    )
    print(f"duckdb: {loaded['database']}")
    transformed = transform_task(spec.key, spec.name)
    featured = export_task(spec.key)
    print(
        f"sequences: {transformed['corners']} corners, "
        f"shot {_fmt_pct(transformed['shot_pct'])}, "
        f"second ball {_fmt_pct(transformed['second_shot_pct'])}"
    )
    print(f"match tape: {featured}")


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"
