CREATE SCHEMA IF NOT EXISTS source;
CREATE SCHEMA IF NOT EXISTS data;

CREATE OR REPLACE FUNCTION data.set_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        NEW.created := CURRENT_TIMESTAMP;
    END IF;
    NEW.updated := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

----------------------------------------
-- DROP VIEWS
----------------------------------------
DROP VIEW data.v_country_stat_1d CASCADE;
DROP VIEW data.v_country_stat_5m CASCADE;
DROP VIEW data.v_country_stat_last CASCADE;
DROP VIEW data.v_neighbours_by_country CASCADE;
DROP VIEW data.v_connectivity_index_by_asn CASCADE;
DROP VIEW data.v_current_asn CASCADE;
DROP VIEW data.vm_asn_neighbour CASCADE;
DROP VIEW data.v_asn_neighbour CASCADE;
DROP VIEW data.vm_connectivity_index_by_country CASCADE;
DROP VIEW data.v_connectivity_index_by_country CASCADE;


DROP TABLE IF EXISTS data.country;
CREATE TABLE data.country (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    c_id SERIAL PRIMARY KEY,
    c_iso2 VARCHAR(2) NOT NULL,
    c_name VARCHAR(256) NOT NULL
);
CREATE TRIGGER trigger_set_timestamps_country
BEFORE INSERT OR UPDATE ON data.country
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();


DROP TABLE IF EXISTS data.country_tag;
CREATE TABLE data.country_tag (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ct_tag VARCHAR(32) NOT NULL,
    ct_country_id INT NOT NULL,
    PRIMARY KEY (ct_tag, ct_country_id),
    FOREIGN KEY (ct_country_id) REFERENCES data.country(c_id) ON DELETE CASCADE
    );
CREATE TRIGGER trigger_set_timestamps_country_tag
BEFORE INSERT OR UPDATE ON data.country_tag
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();


DROP TABLE IF EXISTS data.asn;
CREATE TABLE data.asn (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    a_id SERIAL PRIMARY KEY,
    a_date TIMESTAMP NOT NULL,
    a_country_iso2 VARCHAR(2) NOT NULL,
    a_ripe_id INTEGER NOT NULL,
    a_is_routed BOOLEAN NOT NULL
);
CREATE TRIGGER trigger_set_timestamps_asn
BEFORE INSERT OR UPDATE ON data.asn
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();

CREATE INDEX idx_asn_ripe_id ON data.asn (a_ripe_id);
CREATE INDEX idx_asn_date ON data.asn (a_date);
CREATE INDEX idx_asn_country ON data.asn (a_country_iso2);


DROP TABLE IF EXISTS data.country_stat;
CREATE TABLE data.country_stat (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cs_id SERIAL PRIMARY KEY,
    cs_country_iso2 VARCHAR(2) NOT NULL,
    cs_stats_timestamp TIMESTAMP NOT NULL,
    cs_stats_resolution VARCHAR(4) NOT NULL,
    cs_v4_prefixes_ris INTEGER,
    cs_v6_prefixes_ris INTEGER,
    cs_asns_ris INTEGER,
    cs_v4_prefixes_stats INTEGER,
    cs_v6_prefixes_stats INTEGER,
    cs_asns_stats INTEGER
);
CREATE TRIGGER trigger_set_timestamps_country_stat
BEFORE INSERT OR UPDATE ON data.country_stat
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();


DROP TABLE IF EXISTS data.country_traffic;
CREATE TABLE data.country_traffic (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cr_id SERIAL PRIMARY KEY,
    cr_country_iso2 VARCHAR(2) NOT NULL,
    cr_date TIMESTAMP NOT NULL,
    cr_traffic NUMERIC NOT NULL
);
CREATE TRIGGER trigger_set_timestamps_country_traffic
BEFORE INSERT OR UPDATE ON data.country_traffic
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();


DROP TABLE IF EXISTS data.country_internet_quality;
CREATE TABLE data.country_internet_quality (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ci_id SERIAL PRIMARY KEY,
    ci_country_iso2 VARCHAR(2) NOT NULL,
    ci_date TIMESTAMP NOT NULL,
    ci_p75 NUMERIC NOT NULL,
    ci_p50 NUMERIC NOT NULL,
    ci_p25 NUMERIC NOT NULL
);
CREATE TRIGGER trigger_set_timestamps_country_internet_quality
BEFORE INSERT OR UPDATE ON data.country_internet_quality
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();

DROP TABLE IF EXISTS data.asn_neighbour;
CREATE TABLE data.asn_neighbour (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    an_asn INTEGER NOT NULL,
    an_neighbour INTEGER NOT NULL,
    an_date TIMESTAMP NOT NULL,
    an_type VARCHAR(32),
    an_power INTEGER NOT NULL,
    an_v4_peers INTEGER,
    an_v6_peers INTEGER,
    CONSTRAINT pk_asn_neighbours PRIMARY KEY (an_asn, an_neighbour, an_type)
);

CREATE TRIGGER trigger_set_timestamps_asn_neighbour
BEFORE INSERT OR UPDATE ON data.asn_neighbour
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();

CREATE INDEX idx_asn_neighbour_asn ON data.asn_neighbour (an_asn);
CREATE INDEX idx_asn_neighbour_neighbour ON data.asn_neighbour (an_neighbour);
CREATE INDEX idx_asn_neighbour_date ON data.asn_neighbour (an_date);
CREATE INDEX idx_asn_neighbour_type ON data.asn_neighbour (an_type);
CREATE INDEX idx_asn_neighbour_asn_date ON data.asn_neighbour (an_asn, an_date);
CREATE INDEX idx_asn_neighbour_asn_neighbour_type ON data.asn_neighbour (an_asn, an_neighbour, an_type);

DROP TABLE IF EXISTS source.api_response;
CREATE TABLE source.api_response (
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ar_id SERIAL PRIMARY KEY,
    ar_url VARCHAR,
    ar_params VARCHAR,
    r_response JSONB
);
CREATE TRIGGER trigger_set_timestamps_api_response
BEFORE INSERT OR UPDATE ON source.api_response
FOR EACH ROW
EXECUTE FUNCTION data.set_timestamps();


---------------------------------------
-- VIEWS
---------------------------------------

-- View for stats with resolution '1d'
CREATE OR REPLACE VIEW data.v_country_stat_1d AS
SELECT data.country_stat.*, data.country.c_name
  FROM data.country_stat
  JOIN data.country on c_iso2 = cs_country_iso2
 WHERE cs_stats_resolution = '1d';

-- View for stats with resolution '5m'
CREATE OR REPLACE VIEW data.v_country_stat_5m AS
SELECT data.country_stat.*, data.country.c_name
  FROM data.country_stat
  JOIN data.country on c_iso2 = cs_country_iso2
 WHERE cs_stats_resolution = '5m';

-- View for last stats available for the country
CREATE OR REPLACE VIEW data.v_country_stat_last AS
WITH last_dates AS
( SELECT cs_country_iso2 AS country,
        MAX(cs_stats_timestamp) AS last_date
    FROM data.country_stat
   WHERE cs_stats_resolution='1d'
   GROUP BY cs_country_iso2
)
SELECT country.c_name, country_stat.*
  FROM data.country_stat
  JOIN last_dates ON (last_date=cs_stats_timestamp AND country=cs_country_iso2)
  JOIN data.country ON c_iso2 = cs_country_iso2
 WHERE cs_stats_resolution='1d';

CREATE OR REPLACE VIEW data.v_asn_neighbour
AS
SELECT an_date,
       an_asn,
       a1.asn_country,
       an_neighbour,
       a2.asn_country as neighbour_country,
       CASE WHEN a1.asn_country <> a2.asn_country THEN TRUE ELSE FALSE END as is_foreign_neighbour,
       an_type,
       an_power,
       an_v4_peers,
       an_v6_peers
  FROM data.asn_neighbour as n
   JOIN data.v_current_asn as a1 ON (a1.asn_id = n.an_asn)
   JOIN data.v_current_asn as a2 ON (a2.asn_id = n.an_neighbour)
 WHERE an_type in ('left', 'right');

CREATE MATERIALIZED VIEW data.vm_asn_neighbour
AS SELECT * FROM data.v_asn_neighbour;

CREATE OR REPLACE VIEW data.v_connectivity_index_by_country
AS
SELECT asn_country,
       an_date as date,
       SUM( CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END ) AS foreign_neighbour_count,
       SUM( CASE WHEN NOT is_foreign_neighbour THEN 1 ELSE 0 END ) AS local_neighbour_count,
       COUNT(*) AS total_neighbour_count,
       sum( CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END ) :: FLOAT / count(*) AS foreign_neighbours_share
  FROM data.v_asn_neighbour
 WHERE asn_country IS NOT NULL
 GROUP BY asn_country,
          an_date;

CREATE MATERIALIZED VIEW data.vm_connectivity_index_by_country
AS SELECT * FROM data.v_connectivity_index_by_country;


CREATE OR REPLACE VIEW data.v_neighbours_by_country
AS
SELECT asn_country,
       neighbour_country,
       count(*) AS neighbours_count
  FROM data.v_asn_neighbour
 GROUP BY asn_country,
          neighbour_country;

CREATE OR REPLACE VIEW data.v_connectivity_index_by_asn
AS
SELECT an_asn,
       asn_country,
       SUM( CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END ) AS foreign_neighbour_count,
       SUM( CASE WHEN NOT is_foreign_neighbour THEN 1 ELSE 0 END ) AS local_neighbour_count,
       COUNT(*) AS total_neighbour_count,
       sum( CASE WHEN is_foreign_neighbour THEN 1 ELSE 0 END ) :: FLOAT / count(*) AS foreign_neighbours_share
  FROM data.v_asn_neighbour
 WHERE asn_country IS NOT NULL
 GROUP BY an_asn, asn_country;


CREATE OR REPLACE VIEW data.v_current_asn
AS
WITH current_asn AS
( SELECT a_ripe_id AS asn_id,
        MAX(COALESCE(a_date, CURRENT_DATE)) as last_updated
    FROM data.asn
   GROUP BY a_ripe_id
)
SELECT asn_id,
       last_updated,
       a_country_iso2 AS asn_country,
       a_is_routed AS is_routed
  FROM data.asn
  JOIN current_asn ON asn_id = a_id AND last_updated = COALESCE(a_date, CURRENT_DATE)