"""First-contact zones use the attacking frame and the pitch constants."""

from tests.harness import PITCH, corner, event, flipped, loc, sequences, warehouse


def _zone(side: str, x: float, y: float, *, defender: bool = False) -> str:
    """A corner, then one contact. Returns the zone label."""
    contact_loc = flipped(x, y) if defender else loc(x, y)
    team_id = 2 if defender else 1
    connection = warehouse(
        [
            corner(side=side, end=(x, y) if not defender else (110, 40)),
            event(
                id="contact",
                index=2,
                total_s=11,
                type="Clearance" if defender else "Ball Receipt*",
                team="Defence" if defender else "Attack",
                team_id=team_id,
                player="Defender" if defender else "Target",
                player_id=20 if defender else 11,
                location=contact_loc,
            ),
        ]
    )
    return sequences(connection)[0][3]


def test_same_side_of_the_six_yard_box_is_near_post():
    # Right flag (y = 0): near post is the low-y side of the six-yard box.
    near_y = (PITCH.six_y_min + PITCH.mouth_y_min) / 2
    far_y = (PITCH.mouth_y_max + PITCH.six_y_max) / 2
    x = (PITCH.six_x_min + PITCH.length) / 2
    assert _zone("right", x, near_y) == "near_post"
    assert _zone("right", x, far_y) == "far_post"
    # Left flag mirrors it.
    assert _zone("left", x, far_y) == "near_post"
    assert _zone("left", x, near_y) == "far_post"


def test_central_six_yard_penalty_spot_edge_and_recycled():
    x_six = (PITCH.six_x_min + PITCH.length) / 2
    x_box = (PITCH.box_x_min + PITCH.six_x_min) / 2
    centre = (PITCH.mouth_y_min + PITCH.mouth_y_max) / 2
    wide = (PITCH.box_y_min + PITCH.six_y_min) / 2
    assert _zone("right", x_six, centre) == "six_yard"
    assert _zone("right", x_box, centre) == "penalty_spot"
    assert _zone("right", x_box, wide) == "edge"
    assert _zone("right", PITCH.box_x_min - 8, centre) == "recycled"


def test_defensive_clearance_is_flipped_into_the_attacking_frame():
    # Stored near the defender's own goal. In the corner taker's frame it is the near post.
    near_y = (PITCH.six_y_min + PITCH.mouth_y_min) / 2
    x = (PITCH.six_x_min + PITCH.length) / 2
    assert _zone("right", x, near_y, defender=True) == "near_post"
