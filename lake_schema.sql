-- Canonical DuckLake DDL for OZI Dashboard
CREATE SCHEMA IF NOT EXISTS data;

-- 1. Dimension & Metadata Tables
CREATE TABLE IF NOT EXISTS data.country (
    c_id INTEGER,
    c_iso2 VARCHAR(2) NOT NULL,
    c_name VARCHAR NOT NULL,
    c_name_ru VARCHAR,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data.country_tag (
    ct_id INTEGER,
    ct_country_id INTEGER,
    ct_tag VARCHAR,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data.etl_load (
    load_id BIGINT NOT NULL,
    start_time TIMESTAMP,
    finish_time TIMESTAMP,
    command TEXT,
    status VARCHAR(20)
);

-- 2. Fact & Ingestion Tables
CREATE TABLE IF NOT EXISTS data.asn (
    a_id INTEGER,
    a_date TIMESTAMP NOT NULL,
    a_country_iso2 VARCHAR(2) NOT NULL,
    a_ripe_id INTEGER NOT NULL,
    a_is_routed BOOLEAN NOT NULL,
    load_id BIGINT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data.asn_neighbour (
    an_id INTEGER,
    an_asn BIGINT NOT NULL,
    an_neighbour BIGINT NOT NULL,
    an_date TIMESTAMP NOT NULL,
    an_type VARCHAR(32),
    an_power INTEGER NOT NULL,
    an_v4_peers INTEGER,
    an_v6_peers INTEGER,
    load_id BIGINT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data.country_stat (
    cs_id INTEGER,
    cs_country_iso2 VARCHAR(2) NOT NULL,
    cs_stats_timestamp TIMESTAMP NOT NULL,
    cs_stats_resolution VARCHAR(4) NOT NULL,
    cs_v4_prefixes_ris INTEGER,
    cs_v6_prefixes_ris INTEGER,
    cs_asns_ris INTEGER,
    cs_v4_prefixes_stats INTEGER,
    cs_v6_prefixes_stats INTEGER,
    cs_asns_stats INTEGER,
    load_id BIGINT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data.country_traffic (
    cr_id INTEGER,
    cr_country_iso2 VARCHAR(2) NOT NULL,
    cr_date TIMESTAMP NOT NULL,
    cr_traffic NUMERIC NOT NULL,
    load_id BIGINT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data.country_internet_quality (
    ci_id INTEGER,
    ci_country_iso2 VARCHAR(2) NOT NULL,
    ci_date TIMESTAMP NOT NULL,
    ci_p75 NUMERIC NOT NULL,
    ci_p50 NUMERIC NOT NULL,
    ci_p25 NUMERIC NOT NULL,
    load_id BIGINT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Native Partition Transforms (Iceberg-compatible order-preserving transforms)
ALTER TABLE data.country_stat SET PARTITIONED BY (cs_stats_resolution, year(cs_stats_timestamp), month(cs_stats_timestamp));
ALTER TABLE data.asn_neighbour SET PARTITIONED BY (year(an_date), month(an_date));
ALTER TABLE data.asn SET PARTITIONED BY (year(a_date), month(a_date));
ALTER TABLE data.country_traffic SET PARTITIONED BY (year(cr_date), month(cr_date));
ALTER TABLE data.country_internet_quality SET PARTITIONED BY (year(ci_date), month(ci_date));

-- 4. Precomputed Materialized-Equivalent Tables (populated by etl/finalize_lake.py)
CREATE TABLE IF NOT EXISTS data.vm_current_asn (
    asn_id BIGINT,
    last_updated TIMESTAMP,
    asn_country VARCHAR
);

CREATE TABLE IF NOT EXISTS data.vm_asn_neighbour (
    an_date TIMESTAMP,
    an_asn BIGINT,
    asn_country VARCHAR,
    an_neighbour BIGINT,
    neighbour_country VARCHAR,
    is_foreign_neighbour BOOLEAN,
    an_type VARCHAR,
    an_power INTEGER,
    an_v4_peers INTEGER,
    an_v6_peers INTEGER
);

CREATE TABLE IF NOT EXISTS data.vm_connectivity_index_by_country (
    asn_country VARCHAR,
    date TIMESTAMP,
    asn_count BIGINT,
    foreign_neighbour_count BIGINT,
    local_neighbour_count BIGINT,
    total_neighbour_count BIGINT,
    foreign_neighbours_share DOUBLE
);

CREATE TABLE IF NOT EXISTS data.vm_connectivity_index_by_asn_top10 (
    an_asn BIGINT,
    an_date TIMESTAMP,
    asn_country VARCHAR,
    foreign_neighbour_count BIGINT,
    local_neighbour_count BIGINT,
    total_neighbour_count BIGINT,
    foreign_neighbours_share DOUBLE,
    rn BIGINT
);

CREATE TABLE IF NOT EXISTS data.vm_connectivity_index_distinct (
    asn_country VARCHAR,
    date TIMESTAMP,
    asn_count BIGINT,
    foreign_neighbour_count BIGINT,
    local_neighbour_count BIGINT,
    total_neighbour_count BIGINT,
    foreign_share_pct DOUBLE
);

-- 5. Views over precomputed tables
CREATE OR REPLACE VIEW data.v_current_asn AS
SELECT asn_id, last_updated, asn_country FROM data.vm_current_asn;

CREATE OR REPLACE VIEW data.v_asn_neighbour AS
SELECT * FROM data.vm_asn_neighbour;

CREATE OR REPLACE VIEW data.v_connectivity_index_by_country AS
SELECT * FROM data.vm_connectivity_index_by_country;

CREATE OR REPLACE VIEW data.v_connectivity_index_by_asn_top10 AS
SELECT * FROM data.vm_connectivity_index_by_asn_top10;

CREATE OR REPLACE VIEW data.v_connectivity_index_distinct AS
SELECT * FROM data.vm_connectivity_index_distinct;

CREATE OR REPLACE VIEW data.v_country_stat_1d AS
SELECT * FROM data.country_stat WHERE cs_stats_resolution = '1d';

CREATE OR REPLACE VIEW data.v_country_stat_5m AS
SELECT * FROM data.country_stat WHERE cs_stats_resolution = '5m';
