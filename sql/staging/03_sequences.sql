-- Attach every later event to its corner until the sequence stops, then label it.
-- Stop before a new restart (throw, goal kick, corner, free kick, kick-off, penalty).
-- Stop before an event more than cutoff_s after the first contact.
-- Stop after a goal for the attacking team.
-- The other team's coordinates are flipped into the corner taker's frame.

CREATE OR REPLACE TABLE staging.corner_events AS
WITH RECURSIVE
numbered AS (
    SELECT
        e.*,
        row_number() OVER (
            PARTITION BY e.match_id, e.period
            ORDER BY e.index, e.id
        ) AS rn
    FROM staging.events e
),
walk AS (
    SELECT
        c.corner_id,
        c.match_id,
        c.period,
        c.team_id AS attack_team_id,
        n.id AS event_id,
        n.rn,
        n.timestamp_s,
        CAST(NULL AS DOUBLE) AS first_contact_ts,
        FALSE AS stop_after
    FROM staging.corners c
    JOIN numbered n
        ON n.match_id = c.match_id
        AND n.id = c.corner_id

    UNION ALL

    SELECT
        w.corner_id,
        w.match_id,
        w.period,
        w.attack_team_id,
        nxt.id AS event_id,
        nxt.rn,
        nxt.timestamp_s,
        CASE
            WHEN w.first_contact_ts IS NOT NULL THEN w.first_contact_ts
            WHEN nxt.is_on_ball THEN nxt.timestamp_s
            ELSE NULL
        END AS first_contact_ts,
        (
            (
                nxt.type = 'Shot'
                AND nxt.team_id = w.attack_team_id
                AND nxt.shot_outcome = 'Goal'
            )
            OR (
                nxt.type = 'Own Goal For'
                AND nxt.team_id = w.attack_team_id
            )
        ) AS stop_after
    FROM walk w
    JOIN numbered nxt
        ON nxt.match_id = w.match_id
        AND nxt.period = w.period
        AND nxt.rn = w.rn + 1
    CROSS JOIN staging.definitions d
    WHERE NOT w.stop_after
        AND NOT nxt.is_restart
        AND (
            w.first_contact_ts IS NULL
            OR coalesce(nxt.timestamp_s, w.timestamp_s)
                <= w.first_contact_ts + d.cutoff_s
        )
)
SELECT
    w.corner_id,
    w.attack_team_id,
    w.first_contact_ts,
    w.stop_after,
    n.match_id,
    n.period,
    n.id AS event_id,
    n.rn,
    n.index,
    n.timestamp_s,
    n.minute,
    n.second,
    n.type,
    n.team,
    n.team_id,
    n.player,
    n.player_id,
    n.pass_type,
    n.x,
    n.y,
    n.end_x,
    n.end_y,
    n.shot_outcome,
    n.shot_xg,
    n.is_on_ball
FROM walk w
JOIN numbered n
    ON n.match_id = w.match_id
    AND n.id = w.event_id;

CREATE OR REPLACE TABLE staging.corner_sequences AS
WITH defs AS (
    SELECT * FROM staging.definitions
),
onball AS (
    SELECT
        ce.*,
        CASE
            WHEN ce.team_id = ce.attack_team_id THEN ce.x
            ELSE d.pitch_length - ce.x
        END AS ax,
        CASE
            WHEN ce.team_id = ce.attack_team_id THEN ce.y
            ELSE d.pitch_width - ce.y
        END AS ay
    FROM staging.corner_events ce
    CROSS JOIN defs d
    WHERE ce.is_on_ball
        AND ce.event_id != ce.corner_id
),
first_contact AS (
    SELECT corner_id, ax, ay, type AS contact_type, rn AS contact_rn
    FROM (
        SELECT
            *,
            row_number() OVER (PARTITION BY corner_id ORDER BY rn) AS contact_n
        FROM onball
    )
    WHERE contact_n = 1
),
shots AS (
    SELECT
        corner_id,
        event_id,
        rn,
        player_id,
        shot_outcome,
        shot_xg,
        row_number() OVER (PARTITION BY corner_id ORDER BY rn) AS shot_n
    FROM staging.corner_events
    WHERE type = 'Shot'
        AND team_id = attack_team_id
),
first_shot AS (
    SELECT * FROM shots WHERE shot_n = 1
),
shot_totals AS (
    SELECT
        corner_id,
        count(*) AS shot_n,
        coalesce(sum(shot_xg), 0) AS shot_xg
    FROM shots
    GROUP BY corner_id
),
-- A receipt or carry by the shooter is still the first contact.
-- Any other on-ball action before the shot makes it a second ball.
other_touch AS (
    SELECT DISTINCT s.corner_id
    FROM first_shot s
    JOIN onball o
        ON o.corner_id = s.corner_id
        AND o.rn < s.rn
    WHERE NOT (
        o.player_id IS NOT DISTINCT FROM s.player_id
        AND o.type IN ('Ball Receipt*', 'Carry')
    )
),
goal_totals AS (
    SELECT corner_id, count(*) AS goals
    FROM staging.corner_events
    WHERE (
        type = 'Shot'
        AND team_id = attack_team_id
        AND shot_outcome = 'Goal'
    )
    OR (
        type = 'Own Goal For'
        AND team_id = attack_team_id
    )
    GROUP BY corner_id
),
crosses AS (
    SELECT DISTINCT ce.corner_id
    FROM staging.corner_events ce
    CROSS JOIN defs d
    WHERE ce.type = 'Pass'
        AND ce.team_id = ce.attack_team_id
        AND ce.event_id != ce.corner_id
        AND ce.end_x >= d.box_x_min
        AND ce.end_y BETWEEN d.box_y_min AND d.box_y_max
),
frame_pick AS (
    SELECT
        c.corner_id,
        c.match_id,
        CASE
            WHEN EXISTS (
                SELECT 1
                FROM raw.freeze_frames f
                WHERE f.match_id = c.match_id
                    AND f.id = c.corner_id
            ) THEN c.corner_id
            WHEN EXISTS (
                SELECT 1
                FROM raw.freeze_frames f
                WHERE f.match_id = c.match_id
                    AND f.id = fs.event_id
            ) THEN fs.event_id
            ELSE NULL
        END AS frame_event_id
    FROM staging.corners c
    LEFT JOIN first_shot fs ON fs.corner_id = c.corner_id
),
frame_counts AS (
    SELECT
        p.corner_id,
        count(*) FILTER (
            WHERE f.teammate
                AND f.x >= d.box_x_min
                AND f.y BETWEEN d.box_y_min AND d.box_y_max
        ) AS box_attackers,
        count(*) FILTER (
            WHERE NOT f.teammate
                AND f.x >= d.box_x_min
                AND f.y BETWEEN d.box_y_min AND d.box_y_max
        ) AS box_defenders,
        count(*) FILTER (
            WHERE f.teammate
                AND f.x >= d.six_x_min
                AND f.y BETWEEN d.six_y_min AND d.six_y_max
        ) AS six_yard_attackers
    FROM frame_pick p
    JOIN raw.freeze_frames f
        ON f.match_id = p.match_id
        AND f.id = p.frame_event_id
    CROSS JOIN defs d
    WHERE p.frame_event_id IS NOT NULL
    GROUP BY p.corner_id
)
SELECT
    c.corner_id,
    c.match_id,
    c.period,
    c.index,
    c.minute,
    c.second,
    c.team,
    c.team_id,
    c.player AS taker,
    c.side,
    c.technique,
    c.is_short,
    c.end_x,
    c.end_y,
    fc.ax AS first_contact_x,
    fc.ay AS first_contact_y,
    CASE
        WHEN c.is_short THEN 'short'
        WHEN fc.corner_id IS NULL THEN 'unknown'
        WHEN fc.ax >= d.six_x_min
            AND fc.ay BETWEEN d.six_y_min AND d.six_y_max
            AND c.side = 'left'
            AND fc.ay > d.mouth_y_max THEN 'near_post'
        WHEN fc.ax >= d.six_x_min
            AND fc.ay BETWEEN d.six_y_min AND d.six_y_max
            AND c.side = 'left'
            AND fc.ay < d.mouth_y_min THEN 'far_post'
        WHEN fc.ax >= d.six_x_min
            AND fc.ay BETWEEN d.six_y_min AND d.six_y_max
            AND c.side = 'right'
            AND fc.ay < d.mouth_y_min THEN 'near_post'
        WHEN fc.ax >= d.six_x_min
            AND fc.ay BETWEEN d.six_y_min AND d.six_y_max
            AND c.side = 'right'
            AND fc.ay > d.mouth_y_max THEN 'far_post'
        WHEN fc.ax >= d.six_x_min
            AND fc.ay BETWEEN d.six_y_min AND d.six_y_max THEN 'six_yard'
        WHEN fc.ax >= d.box_x_min
            AND fc.ay BETWEEN d.box_y_min AND d.box_y_max
            AND fc.ay BETWEEN d.corridor_y_min AND d.corridor_y_max THEN 'penalty_spot'
        WHEN fc.ax >= d.box_x_min
            AND fc.ay BETWEEN d.box_y_min AND d.box_y_max THEN 'edge'
        ELSE 'recycled'
    END AS first_contact_zone,
    CASE
        WHEN fc.contact_type = 'Own Goal For' THEN 'goal_first'
        WHEN fs.corner_id IS NOT NULL
            AND ot.corner_id IS NULL
            AND fs.shot_outcome = 'Goal' THEN 'goal_first'
        WHEN fs.corner_id IS NOT NULL
            AND ot.corner_id IS NULL THEN 'shot_first'
        WHEN coalesce(g.goals, 0) > 0 THEN 'second_ball_goal'
        WHEN coalesce(st.shot_n, 0) > 0 THEN 'second_ball_shot'
        WHEN c.is_short AND cr.corner_id IS NOT NULL THEN 'short_then_cross'
        ELSE 'cleared'
    END AS outcome,
    coalesce(st.shot_xg, 0) AS shot_xg,
    coalesce(g.goals, 0) AS goals,
    (fr.corner_id IS NOT NULL) AS has_freeze_frame,
    fr.box_attackers,
    fr.box_defenders,
    fr.six_yard_attackers
FROM staging.corners c
CROSS JOIN defs d
LEFT JOIN first_contact fc ON fc.corner_id = c.corner_id
LEFT JOIN first_shot fs ON fs.corner_id = c.corner_id
LEFT JOIN other_touch ot ON ot.corner_id = c.corner_id
LEFT JOIN shot_totals st ON st.corner_id = c.corner_id
LEFT JOIN goal_totals g ON g.corner_id = c.corner_id
LEFT JOIN crosses cr ON cr.corner_id = c.corner_id
LEFT JOIN frame_counts fr ON fr.corner_id = c.corner_id;
