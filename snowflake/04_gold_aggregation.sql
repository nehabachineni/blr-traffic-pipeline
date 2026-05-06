 -- 04_gold_aggregation.sql

-- Three views built on SILVER.TRAFFIC_FLATTENED

-- 1. CONGESTION_BANDS  Power BI dashboard feed

-- 2. CORRIDOR_STATS  Statistical profile per corridor

-- 3. DISPATCH_WINDOWS  Logistics recommendation engine 


USE DATABASE TRAFFIC_PIPELINE;
USE SCHEMA GOLD;

 --  View 1: Congestion Bands 

-- Rolling 3-reading average per corridor , for smoothing

-- GREEN < 1.2 / YELLOW 1.2-1.8 / RED > 1.8

-- This is what Power BI reads directly 

CREATE OR REPLACE VIEW TRAFFIC_PIPELINE.GOLD.CONGESTION_BANDS AS
WITH math_step AS(
    SELECT
        route_id,
        recorded_at,
        recorded_at_ist,
        ist_hour,
        time_window,
        day_name,
        live_mins,
        ratio AS raw_ratio,

--Using CTE as SQL cant use SQL cannot see rolling_avg in the CASE statement because they are in the same SELECT block.

        ROUND(
            AVG(ratio) OVER(
                PARTITION BY route_id
                ORDER BY recorded_at
                ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
            ),3
      ) AS rolling_avg
    FROM TRAFFIC_PIPELINE.SILVER.TRAFFIC_FLATTENED
  )
SELECT *,
CASE
    WHEN rolling_avg < 1.2  THEN 'GREEN'
    WHEN rolling_avg < 1.8  THEN 'YELLOW'
    ELSE                         'RED'
END                      AS congestion_band

FROM math_step;                                             -- Final view output


--View 2: Corridor Stats
-- Statistical profile per corridor per IST hour
-- Helps us understand which roads are "consistent" vs "unpredictable"

CREATE OR REPLACE VIEW TRAFFIC_PIPELINE.GOLD.CORRIDOR_STATS AS
SELECT
    route_id,
    day_name,
    ist_hour,
    time_window,

    -- Count: How many times have we seen this road at this hour?
    COUNT(*)                                    AS total_observations,

    -- Averages: The Standard expectation
    ROUND(AVG(ratio), 3)                        AS avg_ratio,

    -- Predictability: High StdDev means the roads ETA is varying a lot
    ROUND(STDDEV(ratio), 3)                     AS unpredictability_score,

    -- Percentiles: The "Worst Case Scenario" (95% of journeys are faster than this)
    ROUND(
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ratio), 3              --Find the 95th percentile within the group of ratios
    )                                           AS p95_ratio,

    -- Practical time metrics
    ROUND(AVG(live_mins), 1)                    AS avg_travel_time_mins,
    ROUND(MAX(live_mins), 1)                    AS record_slowest_time

FROM TRAFFIC_PIPELINE.SILVER.TRAFFIC_FLATTENED
WHERE quality_flag = 'VALID'                         --already done in silver layer output, but safety sake
  AND time_window != 'BLACKOUT'                      --scheduler.py works fine, but safety sake
GROUP BY 1, 2, 3, 4; -- Groups by Route, Day, Hour, and Window



-- View 3:Dispatch Windows
-- Answers: "When is the safest time to move cargo?"
-- Combines Average Ratio (Speed) + Variance (Predictability)

CREATE OR REPLACE VIEW TRAFFIC_PIPELINE.GOLD.DISPATCH_WINDOWS AS
WITH hourly_metrics AS(

    SELECT
        route_id,
        day_name,
        ist_hour,
        time_window,
        AVG(ratio)                              AS raw_avg_ratio,
        STDDEV(ratio)                           AS unpredictability,
        COUNT(*)                                AS observations
    FROM TRAFFIC_PIPELINE.SILVER.TRAFFIC_FLATTENED
    WHERE time_window != 'BLACKOUT'
    GROUP BY 1, 2, 3, 4

)
SELECT
    route_id,
    day_name,
    ist_hour,
    time_window,
    observations,
    ROUND(raw_avg_ratio, 2)                         AS avg_ratio,
    ROUND(unpredictability, 2)                      AS risk_factor,

    CASE
        WHEN avg_ratio < 1.15 AND unpredictability < 0.10 THEN 'OPTIMAL'
        WHEN avg_ratio < 1.40 AND unpredictability < 0.20 THEN 'ACCEPTABLE'
        WHEN avg_ratio < 1.70                             THEN 'AVOID_IF_POSSIBLE'
        ELSE                                                   'AVOID'
    END AS dispatch_recommendation

FROM hourly_metrics
ORDER BY route_id, ist_hour;






