-- Headline rates per team. Inswing / outswing / straight are shares of deliveries,
-- not of every corner. rankable is false below the sample floor; the rate is still stored.

CREATE OR REPLACE TABLE marts.team_corners AS
WITH defs AS (
    SELECT * FROM staging.definitions
),
meta AS (
    SELECT * FROM staging.meta
)
SELECT
    s.team_id,
    any_value(s.team) AS team,
    any_value(meta.competition_key) AS competition,
    count(*) AS corners,
    count(*) FILTER (WHERE s.is_short) AS short_n,
    count(*) FILTER (WHERE NOT s.is_short) AS deliveries,
    count(*) FILTER (WHERE s.technique = 'inswing') AS inswing_n,
    count(*) FILTER (WHERE s.technique = 'outswing') AS outswing_n,
    count(*) FILTER (WHERE s.technique = 'straight') AS straight_n,
    count(*) FILTER (WHERE s.technique = 'unknown') AS unknown_n,
    round(
        100.0 * count(*) FILTER (WHERE s.is_short) / nullif(count(*), 0),
        1
    ) AS short_pct,
    round(
        100.0 * count(*) FILTER (WHERE s.technique = 'inswing')
            / nullif(count(*) FILTER (WHERE NOT s.is_short), 0),
        1
    ) AS inswing_pct,
    round(
        100.0 * count(*) FILTER (WHERE s.technique = 'outswing')
            / nullif(count(*) FILTER (WHERE NOT s.is_short), 0),
        1
    ) AS outswing_pct,
    round(
        100.0 * count(*) FILTER (WHERE s.technique = 'straight')
            / nullif(count(*) FILTER (WHERE NOT s.is_short), 0),
        1
    ) AS straight_pct,
    count(*) FILTER (
        WHERE s.outcome IN ('shot_first', 'goal_first', 'second_ball_shot', 'second_ball_goal')
    ) AS shot_n,
    round(
        100.0 * count(*) FILTER (
            WHERE s.outcome IN ('shot_first', 'goal_first', 'second_ball_shot', 'second_ball_goal')
        ) / nullif(count(*), 0),
        1
    ) AS shot_pct,
    count(*) FILTER (WHERE s.outcome IN ('shot_first', 'goal_first')) AS first_shot_n,
    round(
        100.0 * count(*) FILTER (WHERE s.outcome IN ('shot_first', 'goal_first'))
            / nullif(count(*), 0),
        1
    ) AS first_shot_pct,
    count(*) FILTER (
        WHERE s.outcome IN ('second_ball_shot', 'second_ball_goal')
    ) AS second_shot_n,
    round(
        100.0 * count(*) FILTER (
            WHERE s.outcome IN ('second_ball_shot', 'second_ball_goal')
        ) / nullif(count(*), 0),
        1
    ) AS second_shot_pct,
    round(sum(s.shot_xg), 3) AS xg,
    round(sum(s.shot_xg) / nullif(count(*), 0), 3) AS xg_per_corner,
    sum(s.goals) AS goals,
    median(s.box_attackers) AS median_box_attackers,
    count(*) FILTER (WHERE s.has_freeze_frame) AS n_with_frame,
    count(*) >= any_value(defs.min_team_rank_n) AS rankable
FROM staging.corner_sequences s
CROSS JOIN defs
CROSS JOIN meta
GROUP BY s.team_id;
