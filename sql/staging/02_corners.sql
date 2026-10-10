-- One row per corner pass. Short vs delivery is decided here, before the zone.
-- A complete pass outside the box and within short_max_distance of the flag is short.
-- Swung passes into the box stay deliveries even when the technique field is missing.

CREATE OR REPLACE TABLE staging.corners AS
WITH defs AS (
    SELECT * FROM staging.definitions
),
parsed AS (
    SELECT
        e.id AS corner_id,
        e.match_id,
        e.period,
        e.index,
        e.timestamp_s,
        e.minute,
        e.second,
        e.team,
        e.team_id,
        e.player,
        e.player_id,
        e.x AS start_x,
        e.y AS start_y,
        e.end_x,
        e.end_y,
        e.pass_technique,
        (e.pass_outcome IS NULL) AS complete,
        sqrt(pow(e.x - e.end_x, 2) + pow(e.y - e.end_y, 2)) AS flag_distance
    FROM staging.events e
    WHERE e.pass_type = 'Corner'
),
classified AS (
    SELECT
        p.*,
        CASE
            WHEN p.start_y >= d.left_y_min THEN 'left'
            ELSE 'right'
        END AS side,
        (
            p.complete
            AND p.end_x IS NOT NULL
            AND p.end_y IS NOT NULL
            AND NOT (
                p.end_x >= d.box_x_min
                AND p.end_y BETWEEN d.box_y_min AND d.box_y_max
            )
            AND p.flag_distance <= d.short_max_distance
        ) AS is_short
    FROM parsed p
    CROSS JOIN defs d
)
SELECT
    corner_id,
    match_id,
    period,
    index,
    timestamp_s,
    minute,
    second,
    team,
    team_id,
    player,
    player_id,
    start_x,
    start_y,
    end_x,
    end_y,
    side,
    is_short,
    CASE
        WHEN is_short THEN 'short'
        WHEN pass_technique = 'Inswinging' THEN 'inswing'
        WHEN pass_technique = 'Outswinging' THEN 'outswing'
        WHEN pass_technique = 'Straight' THEN 'straight'
        ELSE 'unknown'
    END AS technique
FROM classified;
