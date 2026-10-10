"""Shots on the first contact, the second ball, and the events that end a corner."""

from tests.harness import PITCH, corner, event, flipped, loc, sequences, warehouse


def _contact_xy() -> tuple[float, float]:
    return (PITCH.six_x_min + 1, (PITCH.six_y_min + PITCH.mouth_y_min) / 2)


def test_shot_as_the_first_on_ball_action_is_shot_first():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(end=(x, y)),
            event(
                id="shot",
                index=2,
                total_s=11,
                type="Shot",
                player="Shooter",
                player_id=11,
                location=loc(x, y),
                shot_outcome="Saved",
                shot_statsbomb_xg=0.12,
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[4] == "shot_first"
    assert row[5] == 0.12
    assert row[6] == 0


def test_receipt_then_shot_by_the_same_player_is_still_shot_first():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(end=(x, y), complete=True),
            event(
                id="receipt",
                index=2,
                total_s=11,
                type="Ball Receipt*",
                player="Shooter",
                player_id=11,
                location=loc(x, y),
            ),
            event(
                id="carry",
                index=3,
                total_s=11.2,
                type="Carry",
                player="Shooter",
                player_id=11,
                location=loc(x, y),
            ),
            event(
                id="shot",
                index=4,
                total_s=11.4,
                type="Shot",
                player="Shooter",
                player_id=11,
                location=loc(x, y),
                shot_outcome="Goal",
                shot_statsbomb_xg=0.2,
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[4] == "goal_first"
    assert row[6] == 1


def test_header_then_shot_is_second_ball():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(end=(110, 40)),
            event(
                id="header",
                index=2,
                total_s=11,
                type="Clearance",
                team="Defence",
                team_id=2,
                player="Defender",
                player_id=20,
                location=flipped(x, y),
            ),
            event(
                id="shot",
                index=3,
                total_s=13,
                type="Shot",
                player="Shooter",
                player_id=11,
                location=loc(108, 40),
                shot_outcome="Blocked",
                shot_statsbomb_xg=0.05,
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[3] == "near_post"
    assert row[4] == "second_ball_shot"
    assert row[5] == 0.05


def test_rebound_goal_after_a_save_is_a_second_ball_goal():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(end=(110, 40)),
            event(
                id="header",
                index=2,
                total_s=11,
                type="Clearance",
                team="Defence",
                team_id=2,
                player="Defender",
                player_id=20,
                location=flipped(x, y),
            ),
            event(
                id="saved",
                index=3,
                total_s=12,
                type="Shot",
                player="Shooter",
                player_id=11,
                location=loc(108, 40),
                shot_outcome="Saved",
                shot_statsbomb_xg=0.04,
            ),
            event(
                id="rebound",
                index=4,
                total_s=14,
                type="Shot",
                player="Poacher",
                player_id=12,
                location=loc(116, 40),
                shot_outcome="Goal",
                shot_statsbomb_xg=0.3,
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[4] == "second_ball_goal"
    assert row[6] == 1
    assert abs(row[5] - 0.34) < 1e-9


def test_own_goal_for_the_attacking_team_counts():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(end=(110, 40)),
            event(
                id="header",
                index=2,
                total_s=11,
                type="Clearance",
                team="Defence",
                team_id=2,
                player="Defender",
                player_id=20,
                location=flipped(x, y),
            ),
            event(
                id="og",
                index=3,
                total_s=12,
                type="Own Goal For",
                team="Attack",
                team_id=1,
                player="Beneficiary",
                player_id=11,
                location=loc(119, 40),
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[4] == "second_ball_goal"
    assert row[6] == 1
    assert row[5] == 0


def test_goal_kick_ends_the_sequence_before_a_later_shot():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(event_id="c1", index=1, total_s=10, end=(110, 40)),
            event(
                id="header",
                index=2,
                total_s=11,
                type="Clearance",
                team="Defence",
                team_id=2,
                player="Defender",
                player_id=20,
                location=flipped(x, y),
            ),
            event(
                id="gk",
                index=3,
                total_s=13,
                type="Pass",
                pass_type="Goal Kick",
                team="Defence",
                team_id=2,
                player="Keeper",
                player_id=1,
                location=loc(5, 40),
                pass_end_location=loc(70, 40),
            ),
            event(
                id="later",
                index=4,
                total_s=15,
                type="Shot",
                location=loc(100, 40),
                shot_outcome="Goal",
                shot_statsbomb_xg=0.4,
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[4] == "cleared"
    assert row[6] == 0
    assert row[5] == 0


def test_shot_after_the_open_play_cutoff_is_not_credited():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(end=(110, 40), total_s=10),
            event(
                id="header",
                index=2,
                total_s=11,
                type="Clearance",
                team="Defence",
                team_id=2,
                player="Defender",
                player_id=20,
                location=flipped(x, y),
            ),
            event(
                id="late",
                index=3,
                total_s=11 + PITCH.cutoff_s + 2,
                type="Shot",
                location=loc(108, 40),
                shot_outcome="Goal",
                shot_statsbomb_xg=0.5,
            ),
        ]
    )
    row = sequences(connection)[0]
    assert row[4] == "cleared"
    assert row[6] == 0


def test_penalty_and_a_new_corner_do_not_extend_the_first_sequence():
    x, y = _contact_xy()
    connection = warehouse(
        [
            corner(event_id="c1", index=1, total_s=10, end=(110, 40)),
            event(
                id="header",
                index=2,
                total_s=11,
                type="Clearance",
                team="Defence",
                team_id=2,
                player="Defender",
                player_id=20,
                location=flipped(x, y),
            ),
            event(
                id="pen",
                index=3,
                total_s=12,
                type="Shot",
                shot_type="Penalty",
                shot_outcome="Goal",
                shot_statsbomb_xg=0.76,
                location=loc(108, 40),
            ),
            corner(
                event_id="c2",
                index=4,
                total_s=30,
                end=(116, 40),
                technique="Straight",
            ),
            event(
                id="shot2",
                index=5,
                total_s=31,
                type="Shot",
                location=loc(116, 40),
                shot_outcome="Off T",
                shot_statsbomb_xg=0.02,
            ),
        ]
    )
    rows = sequences(connection)
    assert len(rows) == 2
    assert rows[0][4] == "cleared"
    assert rows[1][1] == "straight"
    assert rows[1][4] == "shot_first"


def test_period_five_produces_no_corners():
    shootout = corner(event_id="pk", period=5, end=(116, 40))
    live = corner(event_id="live", period=2, index=1, total_s=5, end=(110, 40))
    connection = warehouse([shootout, live])
    rows = sequences(connection)
    assert [row[0] for row in rows] == ["live"]
