-- Fact table: one row per fight, enriched with the event date
-- Joins cleaned fights with cleaned events to add the time dimension

SELECT
    f.fight_id,
    f.event_name,
    e.event_date,
    f.fighter_1,
    f.fighter_2,
    f.winner,
    f.weight_class,
    f.method,
    f.round
FROM {{ ref('stg_fight_results') }} AS f
LEFT JOIN {{ ref('stg_event_details') }} AS e
    ON f.event_name = e.event_name