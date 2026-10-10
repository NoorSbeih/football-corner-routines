"""StatsBomb open data to a local parquet cache.

A second build reads the cache and does not call the network when every
match already has an events file and a frames file (an empty frames file
means that match has no 360 dump).
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from corner_routines.config import events_dir, frames_dir, matches_path

EventFetcher = Callable[[int], pd.DataFrame]
MatchFetcher = Callable[[int, int], pd.DataFrame]
FrameFetcher = Callable[[int], pd.DataFrame]

FRAME_COLUMNS = ["match_id", "id", "teammate", "actor", "keeper", "x", "y"]


@dataclass(frozen=True)
class ExtractResult:
    match_count: int
    matches_http: bool
    event_http_fetches: int
    frame_http_fetches: int
    matches_with_360: int

    @property
    def from_cache(self) -> bool:
        return (
            not self.matches_http and self.event_http_fetches == 0 and self.frame_http_fetches == 0
        )


class StatsBombClient:
    """Open-data client. No credentials."""

    def matches(self, competition_id: int, season_id: int) -> pd.DataFrame:
        from statsbombpy import sb

        _silence_open_data_warning()
        return sb.matches(competition_id=competition_id, season_id=season_id)

    def events(self, match_id: int) -> pd.DataFrame:
        from statsbombpy import sb

        _silence_open_data_warning()
        return sb.events(match_id=match_id)

    def frames(self, match_id: int) -> pd.DataFrame:
        from statsbombpy import sb

        _silence_open_data_warning()
        return sb.frames(match_id=match_id)


def extract_competition(
    *,
    competition_key: str,
    competition_id: int,
    season_id: int,
    root: Path,
    matches_fetcher: MatchFetcher | None = None,
    events_fetcher: EventFetcher | None = None,
    frames_fetcher: FrameFetcher | None = None,
    workers: int = 6,
) -> ExtractResult:
    client = StatsBombClient()
    fetch_matches = matches_fetcher or client.matches
    fetch_events = events_fetcher or client.events
    fetch_frames = frames_fetcher or client.frames

    matches_file = matches_path(root, competition_key)
    event_folder = events_dir(root, competition_key)
    frame_folder = frames_dir(root, competition_key)
    event_folder.mkdir(parents=True, exist_ok=True)
    frame_folder.mkdir(parents=True, exist_ok=True)

    matches_http = False
    if matches_file.exists():
        matches = pd.read_parquet(matches_file)
    else:
        matches = fetch_matches(competition_id, season_id)
        matches_http = True
        _write_parquet(matches, matches_file)

    if "match_id" not in matches.columns:
        raise ValueError("matches parquet is missing match_id")

    match_ids = [int(match_id) for match_id in matches["match_id"].tolist()]
    missing_events = [
        match_id for match_id in match_ids if not _event_file(event_folder, match_id).exists()
    ]
    missing_frames = [
        match_id for match_id in match_ids if not _frame_file(frame_folder, match_id).exists()
    ]

    event_fetches = 0
    frame_fetches = 0
    if missing_events:
        print(
            f"fetching {len(missing_events)} event files "
            f"({len(match_ids) - len(missing_events)} already cached)"
        )
        _fetch_parallel(missing_events, event_folder, fetch_events, workers, kind="events")
        event_fetches = len(missing_events)
    if missing_frames:
        print(
            f"fetching {len(missing_frames)} freeze-frame files "
            f"({len(match_ids) - len(missing_frames)} already cached)"
        )
        _fetch_parallel(
            missing_frames,
            frame_folder,
            lambda match_id: _frame_table(fetch_frames(match_id), match_id),
            workers,
            kind="frames",
        )
        frame_fetches = len(missing_frames)

    with_360 = sum(
        1 for match_id in match_ids if _parquet_rows(_frame_file(frame_folder, match_id)) > 0
    )
    return ExtractResult(
        match_count=len(match_ids),
        matches_http=matches_http,
        event_http_fetches=event_fetches,
        frame_http_fetches=frame_fetches,
        matches_with_360=with_360,
    )


def cache_is_complete(root: Path, competition_key: str) -> bool:
    matches_file = matches_path(root, competition_key)
    if not matches_file.exists():
        return False
    matches = pd.read_parquet(matches_file)
    if matches.empty or "match_id" not in matches.columns:
        return False
    event_folder = events_dir(root, competition_key)
    frame_folder = frames_dir(root, competition_key)
    return all(
        _event_file(event_folder, int(match_id)).exists()
        and _frame_file(frame_folder, int(match_id)).exists()
        for match_id in matches["match_id"]
    )


def empty_frames(match_id: int | None = None) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "match_id": pd.Series(dtype="int64"),
            "id": pd.Series(dtype="string"),
            "teammate": pd.Series(dtype="boolean"),
            "actor": pd.Series(dtype="boolean"),
            "keeper": pd.Series(dtype="boolean"),
            "x": pd.Series(dtype="float64"),
            "y": pd.Series(dtype="float64"),
        }
    )
    if match_id is not None:
        frame.attrs["match_id"] = match_id
    return frame


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Make a statsbombpy frame writable as parquet.

    Lists and dicts become JSON strings. ``location`` is therefore a string
    like ``[120.0, 80.0]``, not two numeric columns.
    """
    out = frame.copy()
    for column in out.columns:
        if out[column].dtype != object:
            continue
        out[column] = _normalize_object_column(out[column])
    return out


def _frame_table(frame: pd.DataFrame, match_id: int) -> pd.DataFrame:
    if frame is None or frame.empty:
        return empty_frames()
    out = frame.copy()
    if "id" not in out.columns and "event_uuid" in out.columns:
        out = out.rename(columns={"event_uuid": "id"})
    xs: list[float | None] = []
    ys: list[float | None] = []
    for value in out["location"].tolist():
        point = _xy(value)
        if point is None:
            xs.append(None)
            ys.append(None)
        else:
            xs.append(point[0])
            ys.append(point[1])
    table = pd.DataFrame(
        {
            "match_id": match_id,
            "id": out["id"].astype("string"),
            "teammate": _bool_series(out, "teammate"),
            "actor": _bool_series(out, "actor"),
            "keeper": _bool_series(out, "keeper"),
            "x": xs,
            "y": ys,
        }
    )
    return table.dropna(subset=["x", "y"]).reset_index(drop=True)


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype="boolean")
    return (
        frame[column].map(lambda value: None if _is_null(value) else bool(value)).astype("boolean")
    )


def _xy(value: object) -> tuple[float, float] | None:
    if _is_null(value):
        return None
    if isinstance(value, str):
        value = json.loads(value)
    if isinstance(value, np.ndarray):
        value = value.tolist()
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return float(value[0]), float(value[1])
    return None


def _fetch_parallel(
    match_ids: list[int],
    folder: Path,
    fetch: Callable[[int], pd.DataFrame],
    workers: int,
    *,
    kind: str,
) -> None:
    workers = max(1, min(workers, len(match_ids)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_fetch_one, match_id, folder, fetch, kind): match_id
            for match_id in match_ids
        }
        done = 0
        for future in as_completed(futures):
            future.result()
            done += 1
            print(f"{kind} {done}/{len(match_ids)}", flush=True)


def _fetch_one(
    match_id: int,
    folder: Path,
    fetch: Callable[[int], pd.DataFrame],
    kind: str,
) -> None:
    destination = folder / f"{match_id}.parquet"
    try:
        frame = fetch(match_id)
    except Exception as exc:
        if kind == "frames" and _is_missing(exc):
            frame = empty_frames()
        else:
            raise
    if kind == "events" and "match_id" not in frame.columns:
        frame = frame.copy()
        frame["match_id"] = match_id
    _write_parquet(frame, destination)


def _is_missing(exc: BaseException) -> bool:
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status == 404


def _event_file(folder: Path, match_id: int) -> Path:
    return folder / f"{match_id}.parquet"


def _frame_file(folder: Path, match_id: int) -> Path:
    return folder / f"{match_id}.parquet"


def _parquet_rows(path: Path) -> int:
    if not path.exists():
        return 0
    import pyarrow.parquet as pq

    return int(pq.ParquetFile(path).metadata.num_rows)


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".parquet.tmp")
    try:
        normalize_frame(frame).to_parquet(temporary, index=False)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _normalize_object_column(series: pd.Series) -> pd.Series:
    values = series.tolist()
    kinds = {_kind(value) for value in values if not _is_null(value)}
    if not kinds or kinds == {"str"}:
        return series.map(lambda value: None if _is_null(value) else str(value)).astype("string")
    if kinds == {"bool"}:
        return series.map(lambda value: None if _is_null(value) else bool(value)).astype("boolean")
    if kinds <= {"list", "dict"}:
        return series.map(_json_or_null).astype("string")
    return series.map(_mixed_cell).astype("string")


def _json_or_null(value: object) -> str | None:
    if _is_null(value):
        return None
    return json.dumps(value, default=_json_default)


def _mixed_cell(value: object) -> str | None:
    if _is_null(value):
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=_json_default)
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    return str(value)


def _kind(value: object) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "bool"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, str):
        return "str"
    return "other"


def _is_null(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, dict, str, bytes, tuple)):
        return False
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return False
    if isinstance(missing, (bool, np.bool_)):
        return bool(missing)
    return False


def _json_default(value: object) -> object:
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot encode {type(value).__name__}")


def _silence_open_data_warning() -> None:
    from statsbombpy.api_client import NoAuthWarning

    warnings.filterwarnings("ignore", category=NoAuthWarning)
