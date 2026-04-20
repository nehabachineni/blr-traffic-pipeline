--SETS UP THE DB AND WH 


CREATE DATABASE IF NOT EXISTS TRAFFIC_PIPELINE;   --makes sql script idempotent 
USE DATABASE TRAFFIC_PIPELINE;

--logical grouping of table/ views their structure
CREATE SCHEMA IF NOT EXISTS BRONZE;         --raw json from api
CREATE SCHEMA IF NOT EXISTS SILVER;         -- cleaned, 
CREATE SCHEMA IF NOT EXISTS GOLD;           -- business ready data


-- compute layer (warehouse engine for query execution)
CREATE WAREHOUSE IF NOT EXISTS TRAFFIC_WH
    WITH WAREHOUSE_SIZE = 'XSMALL' --small compute size
    AUTO_SUSPEND = 60               --shuts down after 60s, no billing burn
    AUTO_RESUME = TRUE;             --auto start on query run

USE WAREHOUSE TRAFFIC_WH;






