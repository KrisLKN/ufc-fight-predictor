-- ML dataset: one row per fight, both fighters' features side by side
-- Self-join on fight_id (unique key); a.fighter < b.fighter removes mirror dupes

SELECT
    a.fight_id,
    a.event_date,

    -- Fighter A
    a.fighter                   AS fighter_a,
    a.fights_before             AS a_fights_before,
    a.wins_before               AS a_wins_before,
    a.win_rate                  AS a_win_rate,
    a.ko_rate                   AS a_ko_rate,
    a.sub_rate                  AS a_sub_rate,
    a.won_previous_fight        AS a_won_previous,
    a.days_since_last_fight     AS a_days_since_last,
    a.age_at_fight              AS a_age,
    a.reach                     AS a_reach,
    a.stance                    AS a_stance,
    a.weight_change             AS a_weight_change,

    -- Fighter B
    b.fighter                   AS fighter_b,
    b.fights_before             AS b_fights_before,
    b.wins_before               AS b_wins_before,
    b.win_rate                  AS b_win_rate,
    b.ko_rate                   AS b_ko_rate,
    b.sub_rate                  AS b_sub_rate,
    b.won_previous_fight        AS b_won_previous,
    b.days_since_last_fight     AS b_days_since_last,
    b.age_at_fight              AS b_age,
    b.reach                     AS b_reach,
    b.stance                    AS b_stance,
    b.weight_change             AS b_weight_change,

    -- Target
    a.did_win                   AS a_won

FROM {{ ref('fct_fighter_features') }} AS a
JOIN {{ ref('fct_fighter_features') }} AS b
    ON  a.fight_id = b.fight_id
    AND a.fighter  < b.fighter