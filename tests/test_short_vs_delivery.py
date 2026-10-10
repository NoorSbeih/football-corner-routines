"""Short corners are one routine. A later cross is not a second corner."""

from tests.harness import PITCH, corner, event, loc, sequences, warehouse


def test_corner_pass_becomes_one_sequence():
    connection = warehouse(
        [
            corner(technique="Inswinging", end=(110, 40)),
            event(
                id="receipt",
                index=2,
                total_s=12,
                type="Ball Receipt*",
                location=loc(110, 40),
            ),
        ]
    )
    rows = sequences(connection)
    assert len(rows) == 1
    assert rows[0][0] == "c1"
    assert rows[0][1] == "inswing"
    assert rows[0][2] is False


def test_technique_keeps_inswing_outswing_and_unknown():
    events = []
    for index, technique, label in (
        (1, "Inswinging", "in"),
        (2, "Outswinging", "out"),
        (3, None, "unk"),
    ):
        events.append(
            corner(
                event_id=label,
                index=index,
                total_s=10 + index,
                technique=technique,
                end=(110, 40),
                complete=technique is None,
            )
        )
    # The null-technique pass ends in the box, so it is a delivery, not a short corner.
    connection = warehouse(events)
    found = {row[0]: row[1] for row in sequences(connection)}
    assert found == {"in": "inswing", "out": "outswing", "unk": "unknown"}


def test_complete_pass_near_the_flag_is_short():
    end_x = PITCH.length - 8
    end_y = 6.0
    connection = warehouse(
        [
            corner(
                technique=None,
                end=(end_x, end_y),
                complete=True,
            )
        ]
    )
    row = sequences(connection)[0]
    assert row[2] is True
    assert row[1] == "short"
    assert row[3] == "short"


def test_end_location_inside_the_box_is_a_delivery():
    connection = warehouse(
        [
            corner(
                technique="Outswinging",
                end=(PITCH.six_x_min - 2, 40),
                complete=True,
            )
        ]
    )
    row = sequences(connection)[0]
    assert row[2] is False
    assert row[1] == "outswing"


def test_incomplete_pass_near_the_flag_is_not_short():
    connection = warehouse(
        [
            corner(
                technique=None,
                end=(PITCH.length - 6, 4),
                complete=False,
            )
        ]
    )
    row = sequences(connection)[0]
    assert row[2] is False
    assert row[1] == "unknown"


def test_short_corner_then_cross_is_one_sequence():
    layoff = (PITCH.length - 8, 6.0)
    connection = warehouse(
        [
            corner(
                technique=None,
                end=layoff,
                complete=True,
            ),
            event(
                id="receipt",
                index=2,
                total_s=11,
                type="Ball Receipt*",
                location=loc(*layoff),
            ),
            event(
                id="cross",
                index=3,
                total_s=13,
                type="Pass",
                pass_outcome="Incomplete",
                location=loc(*layoff),
                pass_end_location=loc(110, 40),
            ),
        ]
    )
    rows = sequences(connection)
    assert len(rows) == 1
    assert rows[0][1] == "short"
    assert rows[0][4] == "short_then_cross"
    assert connection.execute("SELECT count(*) FROM staging.corners").fetchone()[0] == 1
