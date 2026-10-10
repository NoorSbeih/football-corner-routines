"""Freeze-frame counts, and the sample-size flag on a routine cell."""

from tests.harness import PITCH, corner, event, loc, warehouse


def _player(event_id: str, x: float, y: float, *, teammate: bool, keeper: bool = False) -> dict:
    return {
        "match_id": 1,
        "id": event_id,
        "teammate": teammate,
        "actor": False,
        "keeper": keeper,
        "x": x,
        "y": y,
    }


def test_box_counts_and_missing_frames():
    inside = (PITCH.box_x_min + 2, 40)
    six = (PITCH.six_x_min + 1, 40)
    outside = (PITCH.box_x_min - 10, 40)
    frames = []
    # 4 attackers in the box, two of them also in the six-yard box. One attacker outside.
    frames.append(_player("c1", six[0], six[1], teammate=True))
    frames.append(_player("c1", six[0], 42, teammate=True))
    frames.append(_player("c1", inside[0], 25, teammate=True))
    frames.append(_player("c1", inside[0], 55, teammate=True))
    frames.append(_player("c1", outside[0], 40, teammate=True))
    for index in range(6):
        frames.append(_player("c1", inside[0], 20 + index, teammate=False, keeper=index == 0))
    connection = warehouse(
        [
            corner(event_id="c1", index=1, total_s=10, end=(110, 40)),
            corner(event_id="c2", index=2, total_s=40, end=(110, 40), technique="Outswinging"),
        ],
        frames,
    )
    rows = connection.execute(
        """
        SELECT corner_id, has_freeze_frame, box_attackers, box_defenders, six_yard_attackers
        FROM staging.corner_sequences
        ORDER BY index
        """
    ).fetchall()
    assert rows[0] == ("c1", True, 4, 6, 2)
    assert rows[1][1] is False
    assert rows[1][2] is None
    assert rows[1][3] is None

    team = connection.execute(
        """
        SELECT median_box_attackers, n_with_frame
        FROM marts.team_corners
        """
    ).fetchone()
    assert team[0] == 4
    assert team[1] == 1


def test_routine_with_three_corners_is_not_reliable():
    events = []
    x = (PITCH.six_x_min + PITCH.length) / 2
    y = (PITCH.six_y_min + PITCH.mouth_y_min) / 2
    for index in range(1, 4):
        events.append(
            corner(
                event_id=f"c{index}",
                index=index * 2 - 1,
                total_s=index * 30,
                end=(x, y),
            )
        )
        events.append(
            event(
                id=f"r{index}",
                index=index * 2,
                total_s=index * 30 + 1,
                type="Ball Receipt*",
                location=loc(x, y),
            )
        )
    connection = warehouse(events)
    reliable, count = connection.execute(
        """
        SELECT reliable, n
        FROM marts.team_routines
        WHERE technique = 'inswing' AND zone = 'near_post'
        """
    ).fetchone()
    assert count == 3
    assert reliable is False


def test_routine_at_the_sample_floor_is_reliable():
    events = []
    x = (PITCH.box_x_min + PITCH.six_x_min) / 2
    y = (PITCH.mouth_y_min + PITCH.mouth_y_max) / 2
    for index in range(1, PITCH.min_routine_n + 1):
        events.append(
            corner(
                event_id=f"c{index}",
                index=index * 2 - 1,
                total_s=index * 20,
                technique="Outswinging",
                end=(x, y),
            )
        )
        events.append(
            event(
                id=f"r{index}",
                index=index * 2,
                total_s=index * 20 + 1,
                type="Ball Receipt*",
                location=loc(x, y),
            )
        )
    connection = warehouse(events)
    reliable, count = connection.execute(
        """
        SELECT reliable, n
        FROM marts.team_routines
        WHERE technique = 'outswing' AND zone = 'penalty_spot'
        """
    ).fetchone()
    assert count == PITCH.min_routine_n
    assert reliable is True
