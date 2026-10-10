"""Competition config, pitch constants, and on-disk paths."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "competitions.yaml"
PITCH_PATH = ROOT / "config" / "pitch.yaml"


class ConfigError(Exception):
    """Raised when a competition key is missing or incomplete."""


@dataclass(frozen=True)
class Competition:
    key: str
    name: str
    competition_id: int
    season_id: int


@dataclass(frozen=True)
class Pitch:
    length: float
    width: float
    box_x_min: float
    box_y_min: float
    box_y_max: float
    six_x_min: float
    six_y_min: float
    six_y_max: float
    mouth_y_min: float
    mouth_y_max: float
    corridor_y_min: float
    corridor_y_max: float
    short_max_distance: float
    cutoff_s: float
    left_y_min: float
    min_routine_n: int
    min_team_rank_n: int


def get_competition(key: str, config_path: Path = CONFIG_PATH) -> Competition:
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    competitions = document.get("competitions") or {}
    raw = competitions.get(key)
    if not isinstance(raw, dict):
        known = ", ".join(sorted(competitions)) or "(none)"
        raise ConfigError(f"Unknown competition {key!r}. Known keys: {known}")
    competition_id = raw.get("competition_id")
    season_id = raw.get("season_id")
    if competition_id is None or season_id is None:
        raise ConfigError(f"Competition {key!r} is missing competition_id or season_id")
    name = raw.get("name") or key
    return Competition(
        key=key,
        name=str(name),
        competition_id=int(competition_id),
        season_id=int(season_id),
    )


def get_pitch(config_path: Path = PITCH_PATH) -> Pitch:
    with config_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    pitch = document["pitch"]
    box = document["penalty_box"]
    six = document["six_yard"]
    mouth = document["goal_mouth"]
    corridor = document["central_corridor"]
    short = document["short_corner"]
    sequence = document["sequence"]
    side = document["side"]
    sample = document["sample"]
    return Pitch(
        length=float(pitch["length"]),
        width=float(pitch["width"]),
        box_x_min=float(box["x_min"]),
        box_y_min=float(box["y_min"]),
        box_y_max=float(box["y_max"]),
        six_x_min=float(six["x_min"]),
        six_y_min=float(six["y_min"]),
        six_y_max=float(six["y_max"]),
        mouth_y_min=float(mouth["y_min"]),
        mouth_y_max=float(mouth["y_max"]),
        corridor_y_min=float(corridor["y_min"]),
        corridor_y_max=float(corridor["y_max"]),
        short_max_distance=float(short["max_distance"]),
        cutoff_s=float(sequence["open_play_cutoff_s"]),
        left_y_min=float(side["left_y_min"]),
        min_routine_n=int(sample["min_routine_n"]),
        min_team_rank_n=int(sample["min_team_rank_n"]),
    )


def raw_dir(root: Path, competition_key: str) -> Path:
    return root / "data" / "raw" / competition_key


def matches_path(root: Path, competition_key: str) -> Path:
    return raw_dir(root, competition_key) / "matches.parquet"


def events_dir(root: Path, competition_key: str) -> Path:
    return raw_dir(root, competition_key) / "events"


def frames_dir(root: Path, competition_key: str) -> Path:
    return raw_dir(root, competition_key) / "frames"


def database_path(root: Path) -> Path:
    return root / "data" / "corner_routines.duckdb"


def web_data_dir(root: Path) -> Path:
    return root / "web" / "public" / "data"
