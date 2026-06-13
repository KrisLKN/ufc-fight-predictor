-- Staging model: clean version of raw_fight_results
-- One row per fight, with readable column names and a clear winner

SELECT
    split_part(URL, '/', -1)       AS fight_id,
    trim(EVENT)                    AS event_name,
    BOUT                           AS bout,
    split_part(BOUT, ' vs. ', 1)   AS fighter_1,
    split_part(BOUT, ' vs. ', 2)   AS fighter_2,
    OUTCOME                        AS outcome,
    CASE
        WHEN OUTCOME = 'W/L' THEN split_part(BOUT, ' vs. ', 1)
        WHEN OUTCOME = 'L/W' THEN split_part(BOUT, ' vs. ', 2)
        ELSE NULL
    END                            AS winner,
    trim(WEIGHTCLASS)                    AS weight_class,
    trim(METHOD)                         AS method,
    CAST(ROUND AS INTEGER)         AS round
FROM {{ source('ufc', 'raw_fight_results') }}