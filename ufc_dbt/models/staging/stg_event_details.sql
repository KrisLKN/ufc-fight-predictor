-- Staging model: clean version of raw_event_details
-- One row per event, with a real date type for time-based calculations

SELECT
    trim(EVENT)                          AS event_name,
    strptime("DATE", '%B %d, %Y')  AS event_date,
    LOCATION                       AS location
FROM {{ source('ufc', 'raw_event_details') }}