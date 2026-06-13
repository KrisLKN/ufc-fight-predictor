-- Staging model: clean version of raw_fighter_tott (fighter profiles)
-- Deduplicated to one profile per fighter name (rare homonyms collapsed)

WITH parsed AS (
    SELECT
        trim(FIGHTER)                                   AS fighter,
        TRY_CAST(replace(REACH, '"', '') AS INTEGER)    AS reach,
        trim(STANCE)                                    AS stance,
        try_strptime("DOB", '%b %d, %Y')                AS date_of_birth,
        ROW_NUMBER() OVER (
            PARTITION BY trim(FIGHTER)
            ORDER BY try_strptime("DOB", '%b %d, %Y')
        )                                               AS rn
    FROM {{ source('ufc', 'raw_fighter_tott') }}
)

SELECT
    fighter,
    reach,
    stance,
    date_of_birth
FROM parsed
WHERE rn = 1