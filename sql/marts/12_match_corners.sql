-- One row per corner sequence, for the match tape and the team pitch.

CREATE OR REPLACE TABLE marts.match_corners AS
SELECT
    corner_id,
    match_id,
    period,
    index,
    minute,
    second,
    team,
    team_id,
    taker,
    side,
    technique,
    is_short,
    end_x,
    end_y,
    first_contact_x,
    first_contact_y,
    first_contact_zone,
    outcome,
    shot_xg,
    goals,
    has_freeze_frame,
    box_attackers,
    box_defenders,
    six_yard_attackers,
    outcome IN ('shot_first', 'goal_first', 'second_ball_shot', 'second_ball_goal') AS shot
FROM staging.corner_sequences;
