-- 05_data_quality.sql
-- Purpose: Monitor the integrity and freshness of the traffic data pipeline.
--ALTER SESSION SET TIMEZONE = 'Asia/Kolkata';
USE DATABASE TRAFFIC_PIPELINE;
USE SCHEMA GOLD;

--  View 1: Quality Report 


CREATE OR REPLACE VIEW TRAFFIC_PIPELINE.GOLD.QUALITY_REPORT AS
SELECT
    route_id,
    recorded_at,
    recorded_at_ist,
    ist_hour,
    time_window,
    live_mins,
    ratio,
    quality_flag,       -- Inherited from Silver

    -- Confidence score 0-100 logic:
    -- View 2 can aggregates it later.
    CASE
        WHEN ratio BETWEEN 0.8 AND 4.0  THEN 100  -- Ideal/Realistic range
        WHEN ratio BETWEEN 0.5 AND 5.0  THEN 75   -- Possible but unusual
        WHEN ratio IS NOT NULL          THEN 50   -- Data exists but outside logic bounds
        ELSE                                  0   -- Missing or null data
    END AS confidence_score

FROM TRAFFIC_PIPELINE.SILVER.TRAFFIC_FLATTENED;


--  View 2: Pipeline Health 
-- This is the  Heartbeat monitor. 
-- It aggregates the Quality Report to show the status of each corridor.

CREATE OR REPLACE VIEW TRAFFIC_PIPELINE.GOLD.PIPELINE_HEALTH AS
WITH base AS (
    SELECT
        route_id,
        COUNT(*)                        AS total_records,
        ROUND(AVG(confidence_score),0) AS avg_confidence,

        MAX(recorded_at)      AS last_record_utc,
        MAX(recorded_at_ist)  AS last_record_ist,


        -- Correct: session TZ to IST
        CONVERT_TIMEZONE('Asia/Kolkata', CURRENT_TIMESTAMP()) AS current_ist,
        HOUR(current_ist) AS current_hour

    FROM TRAFFIC_PIPELINE.GOLD.QUALITY_REPORT
    GROUP BY route_id
),

mins_since_last_step AS (
    SELECT *,
        DATEDIFF(
            'minute',
          last_record_ist::TIMESTAMP_NTZ,
          current_ist::TIMESTAMP_NTZ
        ) AS mins_since_last
    FROM base
)

SELECT
    *,
    CASE
        -- Blackout hours (11 PM - 7 AM IST)
        WHEN current_hour >= 23
          OR current_hour < 7
            THEN 'BLACKOUT_EXPECTED'

        -- Midday check (11 AM - 3 PM IST)
        WHEN current_hour BETWEEN 11 AND 15 THEN
              CASE
                    WHEN mins_since_last > 75 THEN 'STALE_MIDDAY'
                    ELSE 'LIVE'
               END

        WHEN mins_since_last > 45
            THEN 'STALE'

        ELSE 'LIVE'
    END AS feed_status

FROM mins_since_last_step
ORDER BY last_record_ist DESC;
