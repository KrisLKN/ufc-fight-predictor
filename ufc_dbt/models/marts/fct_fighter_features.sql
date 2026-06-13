-- Feature table: one row per fighter per fight
-- Career + form + profile + style + weight-class change (up/down/same)
-- All cumulative features use only PAST fights (frame ends at 1 PRECEDING)

WITH flagged AS (
    SELECT
        f.fight_id, f.fighter, f.opponent, f.event_date, f.weight_class, f.did_win,
        d.reach, d.stance, d.date_of_birth,

        CASE WHEN f.did_win = 1 AND f.method IN ('KO/TKO', 'TKO - Doctor''s Stoppage')
             THEN 1 ELSE 0 END AS is_ko_win,
        CASE WHEN f.did_win = 1 AND f.method = 'Submission'
             THEN 1 ELSE 0 END AS is_sub_win,

        -- Normalize weight class (most specific FIRST!)
        CASE
            WHEN f.weight_class LIKE '%Women''s Strawweight%'   THEN 'W_Strawweight'
            WHEN f.weight_class LIKE '%Women''s Flyweight%'     THEN 'W_Flyweight'
            WHEN f.weight_class LIKE '%Women''s Bantamweight%'  THEN 'W_Bantamweight'
            WHEN f.weight_class LIKE '%Women''s Featherweight%' THEN 'W_Featherweight'
            WHEN f.weight_class LIKE '%Flyweight%'              THEN 'Flyweight'
            WHEN f.weight_class LIKE '%Bantamweight%'           THEN 'Bantamweight'
            WHEN f.weight_class LIKE '%Featherweight%'          THEN 'Featherweight'
            WHEN f.weight_class LIKE '%Lightweight%'            THEN 'Lightweight'
            WHEN f.weight_class LIKE '%Welterweight%'           THEN 'Welterweight'
            WHEN f.weight_class LIKE '%Middleweight%'           THEN 'Middleweight'
            WHEN f.weight_class LIKE '%Light Heavyweight%'      THEN 'Light_Heavyweight'
            WHEN f.weight_class LIKE '%Heavyweight%'            THEN 'Heavyweight'
            ELSE 'Other'
        END AS wc_clean
    FROM {{ ref('int_fighter_fights') }} AS f
    LEFT JOIN {{ ref('stg_fighter_details') }} AS d
        ON f.fighter = d.fighter
),

ranked AS (
    SELECT
        *,
        -- Numeric rank per division (men and women on SEPARATE scales)
        CASE wc_clean
            WHEN 'Flyweight'         THEN 1
            WHEN 'Bantamweight'      THEN 2
            WHEN 'Featherweight'     THEN 3
            WHEN 'Lightweight'       THEN 4
            WHEN 'Welterweight'      THEN 5
            WHEN 'Middleweight'      THEN 6
            WHEN 'Light_Heavyweight' THEN 7
            WHEN 'Heavyweight'       THEN 8
            WHEN 'W_Strawweight'     THEN 101
            WHEN 'W_Flyweight'       THEN 102
            WHEN 'W_Bantamweight'    THEN 103
            WHEN 'W_Featherweight'   THEN 104
            ELSE NULL   -- 'Other' (tournaments, catch/open weight): no rank
        END AS wc_rank
    FROM flagged
),

base AS (
    SELECT
        *,
        date_diff('year', date_of_birth, event_date)               AS age_at_fight,

        ROW_NUMBER() OVER (PARTITION BY fighter ORDER BY event_date) - 1   AS fights_before,

        COALESCE(SUM(did_win) OVER (
            PARTITION BY fighter ORDER BY event_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)   AS wins_before,

        COALESCE(SUM(is_ko_win) OVER (
            PARTITION BY fighter ORDER BY event_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)   AS ko_wins_before,

        COALESCE(SUM(is_sub_win) OVER (
            PARTITION BY fighter ORDER BY event_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), 0)   AS sub_wins_before,

        LAG(did_win) OVER (PARTITION BY fighter ORDER BY event_date)       AS won_previous_fight,

        date_diff('day',
            LAG(event_date) OVER (PARTITION BY fighter ORDER BY event_date),
            event_date)                                            AS days_since_last_fight,

        -- Rank of the PREVIOUS fight's division
        LAG(wc_rank) OVER (PARTITION BY fighter ORDER BY event_date)       AS prev_wc_rank
    FROM ranked
)

SELECT
    *,
    CASE WHEN fights_before = 0 THEN 0
         ELSE wins_before * 1.0 / fights_before END                AS win_rate,
    CASE WHEN wins_before = 0 THEN 0
         ELSE ko_wins_before  * 1.0 / wins_before END              AS ko_rate,
    CASE WHEN wins_before = 0 THEN 0
         ELSE sub_wins_before * 1.0 / wins_before END              AS sub_rate,

    -- Weight class change vs previous fight: +1 up, -1 down, 0 same, NULL if unknown
    CASE
        WHEN wc_rank IS NULL OR prev_wc_rank IS NULL THEN NULL
        WHEN wc_rank > prev_wc_rank THEN 1     -- moved UP (heavier)
        WHEN wc_rank < prev_wc_rank THEN -1    -- moved DOWN (lighter)
        ELSE 0                                  -- same division
    END AS weight_change
FROM base