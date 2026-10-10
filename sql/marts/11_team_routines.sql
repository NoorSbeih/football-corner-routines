-- Technique x first-contact zone. reliable is false below min_routine_n.
-- The rate is stored either way; the UI withholds it when reliable is false.

CREATE OR REPLACE TABLE marts.team_routines AS
WITH defs AS (
    SELECT * FROM staging.definitions
)
SELECT
    s.team_id,
    any_value(s.team) AS team,
    s.technique,
    s.first_contact_zone AS zone,
    count(*) AS n,
    count(*) FILTER (
        WHERE s.outcome IN ('shot_first', 'goal_first', 'second_ball_shot', 'second_ball_goal')
    ) AS shot_n,
    round(
        100.0 * count(*) FILTER (
            WHERE s.outcome IN ('shot_first', 'goal_first', 'second_ball_shot', 'second_ball_goal')
        ) / nullif(count(*), 0),
        1
    ) AS shot_pct,
    round(sum(s.shot_xg) / nullif(count(*), 0), 3) AS xg_per_corner,
    sum(s.goals) AS goals,
    count(*) >= any_value(defs.min_routine_n) AS reliable
FROM staging.corner_sequences s
CROSS JOIN defs
GROUP BY s.team_id, s.technique, s.first_contact_zone;
