--not losing original raw data

CREATE TABLE IF NOT EXISTS TRAFFIC_PIPELINE.BRONZE.TRAFFIC_RAW(
 --columns
    ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), -- when snowflake received the record, time based analysis/ debugging 
    route_id VARCHAR(100),    --corridor in blr, can group traffic by route
    raw_payload VARIANT,      --flexible JSON container , change resistant
    kafka_partition NUMBER,   --which kafka partition origin
    kafka_offset NUMBER      ---pos of msg in stream 


);










