-- Intermediate model: one row per fighter per fight (unpivoted)

-- Point of view of fighter_1
SELECT
    fight_id,
    event_date,
    event_name,
    fighter_1                          AS fighter,
    fighter_2                          AS opponent,
    CASE WHEN winner = fighter_1 THEN 1 ELSE 0 END AS did_win,
    weight_class,
    method
FROM {{ ref('fct_fights') }}

UNION ALL

-- Point of view of fighter_2
SELECT
    fight_id,
    event_date,
    event_name,
    fighter_2                          AS fighter,
    fighter_1                          AS opponent,
    CASE WHEN winner = fighter_2 THEN 1 ELSE 0 END AS did_win,
    weight_class,
    method
FROM {{ ref('fct_fights') }}