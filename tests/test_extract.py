"""The parquet cache is not fetched twice."""

from pathlib import Path

import pandas as pd

from corner_routines.extract import extract_competition


def _matches() -> pd.DataFrame:
    return pd.DataFrame({"match_id": [7], "home_team": ["A"], "away_team": ["B"]})


def test_second_build_does_not_refetch(tmp_path: Path):
    calls = {"matches": 0, "events": 0, "frames": 0}

    def matches(competition_id: int, season_id: int) -> pd.DataFrame:
        calls["matches"] += 1
        return _matches()

    def events(match_id: int) -> pd.DataFrame:
        calls["events"] += 1
        return pd.DataFrame(
            {
                "id": ["e1"],
                "match_id": [match_id],
                "type": ["Pass"],
                "location": [[120.0, 0.1]],
            }
        )

    def frames(match_id: int) -> pd.DataFrame:
        calls["frames"] += 1
        return pd.DataFrame(
            {
                "id": ["e1"],
                "match_id": [match_id],
                "teammate": [True],
                "actor": [False],
                "keeper": [False],
                "location": [[110.0, 40.0]],
            }
        )

    kwargs = {
        "competition_key": "wc2022",
        "competition_id": 43,
        "season_id": 106,
        "root": tmp_path,
        "matches_fetcher": matches,
        "events_fetcher": events,
        "frames_fetcher": frames,
        "workers": 1,
    }
    first = extract_competition(**kwargs)
    second = extract_competition(**kwargs)
    assert first.event_http_fetches == 1
    assert first.frame_http_fetches == 1
    assert first.matches_with_360 == 1
    assert second.from_cache
    assert calls == {"matches": 1, "events": 1, "frames": 1}


def test_missing_360_file_is_cached_empty(tmp_path: Path):
    import requests

    def matches(competition_id: int, season_id: int) -> pd.DataFrame:
        return _matches()

    def events(match_id: int) -> pd.DataFrame:
        return pd.DataFrame({"id": ["e1"], "type": ["Pass"], "match_id": [match_id]})

    def frames(match_id: int) -> pd.DataFrame:
        response = requests.Response()
        response.status_code = 404
        raise requests.HTTPError(response=response)

    result = extract_competition(
        competition_key="wc2022",
        competition_id=43,
        season_id=106,
        root=tmp_path,
        matches_fetcher=matches,
        events_fetcher=events,
        frames_fetcher=frames,
        workers=1,
    )
    assert result.matches_with_360 == 0
    assert (tmp_path / "data" / "raw" / "wc2022" / "frames" / "7.parquet").exists()
    again = extract_competition(
        competition_key="wc2022",
        competition_id=43,
        season_id=106,
        root=tmp_path,
        matches_fetcher=matches,
        events_fetcher=events,
        frames_fetcher=frames,
        workers=1,
    )
    assert again.frame_http_fetches == 0
