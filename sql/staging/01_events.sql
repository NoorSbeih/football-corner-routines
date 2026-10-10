-- One row per event in periods 1–4. Period 5 is the penalty shootout.
-- Locations stay in the event team's frame. The sequence step flips them.

CREATE OR REPLACE TABLE staging.events AS
SELECT
    try_cast(match_id AS BIGINT) AS match_id,
    id::VARCHAR AS id,
    try_cast(period AS INTEGER) AS period,
    try_cast(index AS INTEGER) AS index,
    coalesce(
        date_diff(
            'microsecond',
            TIME '00:00:00',
            try_cast(timestamp AS TIME)
        ) / 1000000.0,
        try_cast(minute AS DOUBLE) * 60 + try_cast(second AS DOUBLE)
    ) AS timestamp_s,
    try_cast(minute AS INTEGER) AS minute,
    try_cast(second AS INTEGER) AS second,
    type::VARCHAR AS type,
    team::VARCHAR AS team,
    try_cast(team_id AS BIGINT) AS team_id,
    player::VARCHAR AS player,
    try_cast(player_id AS BIGINT) AS player_id,
    pass_type::VARCHAR AS pass_type,
    pass_outcome::VARCHAR AS pass_outcome,
    pass_technique::VARCHAR AS pass_technique,
    try_cast(json_extract(location, '$[0]') AS DOUBLE) AS x,
    try_cast(json_extract(location, '$[1]') AS DOUBLE) AS y,
    try_cast(json_extract(pass_end_location, '$[0]') AS DOUBLE) AS end_x,
    try_cast(json_extract(pass_end_location, '$[1]') AS DOUBLE) AS end_y,
    shot_outcome::VARCHAR AS shot_outcome,
    try_cast(shot_statsbomb_xg AS DOUBLE) AS shot_xg,
    shot_type::VARCHAR AS shot_type,
    goalkeeper_type::VARCHAR AS goalkeeper_type,
    (
        type IN (
            'Ball Receipt*',
            'Pass',
            'Carry',
            'Clearance',
            'Ball Recovery',
            'Shot',
            'Block',
            'Miscontrol',
            'Dribble',
            'Dispossessed',
            'Interception',
            '50/50',
            'Shield',
            'Own Goal For'
        )
        OR (
            type = 'Goal Keeper'
            AND goalkeeper_type IN ('Punch', 'Collected', 'Keeper Sweeper', 'Smother', 'Save')
        )
    ) AS is_on_ball,
    (
        coalesce(pass_type, '') IN ('Throw-in', 'Goal Kick', 'Corner', 'Free Kick', 'Kick Off')
        OR coalesce(shot_type, '') = 'Penalty'
        OR type IN ('Half End', 'Half Start')
    ) AS is_restart
FROM raw.events
WHERE try_cast(period AS INTEGER) BETWEEN 1 AND 4;
