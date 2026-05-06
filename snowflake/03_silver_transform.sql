-- 03_silver_transform.sql
-- Reads from actual Bronze table
-- Deduplicates using Kafka offset + partition
-- Filters for Production start: May 5th, 2026

USE DATABASE TRAFFIC_PIPELINE;
USE SCHEMA SILVER;


-- 1. VIEWS: A "live window" that transforms raw JSON into clean columns in real-time without storing a duplicate copy of the data.  
-- 2. MATERIALIZATION: The act of physically saving query results into a table for faster performance on massive datasets.
-- 3. WHEN TO USE: Use Views for flexibility and real-time freshness; switch to Materialization when queries become slow/expensive.
-- 4. DYNAMIC TABLES: A Snowflake hybrid that automatically refreshes a physical table based on a SQL query to ensure "Target Freshness."

CREATE OR REPLACE VIEW TRAFFIC_PIPELINE.SILVER.TRAFFIC_FLATTENED AS

WITH raw AS (                                                                   --CTE 1 "raw"

    SELECT

        RECORD_METADATA:offset::NUMBER        AS kafka_offset,
        RECORD_METADATA:partition::NUMBER     AS kafka_partition,
        RECORD_METADATA:topic::VARCHAR        AS kafka_topic,

        -- Core corridor data
        RECORD_CONTENT:route_id::VARCHAR      AS route_id,
        RECORD_CONTENT:live_seconds::NUMBER   AS live_seconds,
        RECORD_CONTENT:ratio::FLOAT           AS ratio,
        RECORD_CONTENT:timestamp::TIMESTAMP   AS recorded_at,    --UTC

        -- Snowflake ingestion time
        -- Using the time Kafka received the message as ingestion timestamp
        RECORD_METADATA:CreateTime::TIMESTAMP AS ingested_at    --IST

    FROM TRAFFIC_PIPELINE.BRONZE.TRAFFIC_RAW_EVENTS_1158454832

    WHERE RECORD_CONTENT:route_id::VARCHAR IS NOT NULL
    AND   RECORD_CONTENT:live_seconds::NUMBER > 0
    -- Only keep records from May 5th onwards
    AND   RECORD_CONTENT:timestamp::TIMESTAMP >= '2026-05-05'::TIMESTAMP

),
 -- Remove duplicates from the Kafka stream
 deduplicated AS (                                                       --CTE 2 "deduplicated"

    SELECT *,                                                            -- Window function , the looks into related rows( partition                                                                               by), adds row numbers , take only yhe first/og record                                                                                hence ASC
        ROW_NUMBER() OVER(
            PARTITION BY kafka_offset, kafka_partition
            ORDER BY recorded_at ASC

        ) AS row_num

    FROM  raw
    QUALIFY row_num = 1

),

enriched AS(                                                        --CTE3 "enriched"
    SELECT
        route_id,
        live_seconds,
        ratio,
        recorded_at,
        ingested_at,
        kafka_offset,
        kafka_partition,

        ROUND(live_seconds / 60.0, 1)         AS live_mins,

        --  Timezone conversion (UTC to IST for Bengaluru context)
        CONVERT_TIMEZONE('UTC', 'Asia/Kolkata', recorded_at) AS recorded_at_ist,

        -- Time context (Based on IST)
        HOUR(recorded_at_ist)                 AS ist_hour,
        DAYNAME(recorded_at_ist)              AS day_name,

        --  Window classification using IST hour

        CASE
            WHEN HOUR(recorded_at_ist) BETWEEN 7 AND 10  THEN 'MORNING_PEAK'
            WHEN HOUR(recorded_at_ist) BETWEEN 11 AND 15 THEN 'MIDDAY'
            WHEN HOUR(recorded_at_ist) BETWEEN 16 AND 22 THEN 'EVENING_PEAK'
            ELSE 'BLACKOUT'
        END                                   AS time_window,                --new column

        --  Data quality checks
        CASE
            WHEN ratio IS NULL          THEN 'NO_RATIO'
            WHEN ratio > 5.0            THEN 'SUSPECT_HIGH'
            WHEN ratio < 0.5            THEN 'SUSPECT_LOW'
            WHEN live_seconds < 60      THEN 'SUSPECT_SHORT'
            ELSE                             'VALID'
        END                                   AS quality_flag

    FROM deduplicated

)


--FINAL OUTPUT OF THE VIEW SILVER.TRAFFIC_FLATTENED
SELECT * FROM enriched
WHERE quality_flag = 'VALID';



