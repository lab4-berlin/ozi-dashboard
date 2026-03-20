-- Migration: Replace asn_neighbour with asn_neighbour_count
-- Stores aggregated neighbour counts per ASN per date instead of individual neighbour records
-- Run this on existing databases before deploying the new ETL logic

\connect ozi_db2

-- Drop dependent objects (materialized views, views) - order matters
DROP MATERIALIZED VIEW IF EXISTS data.vm_asn_neighbour CASCADE;
DROP MATERIALIZED VIEW IF EXISTS data.vm_connectivity_index_by_asn_top10 CASCADE;
DROP MATERIALIZED VIEW IF EXISTS data.vm_connectivity_index_by_country CASCADE;

DROP VIEW IF EXISTS data.v_neighbours_by_country CASCADE;
DROP VIEW IF EXISTS data.v_connectivity_index_distinct CASCADE;
DROP VIEW IF EXISTS data.v_connectivity_index_by_country CASCADE;
DROP VIEW IF EXISTS data.v_connectivity_index_by_asn_top10 CASCADE;
DROP VIEW IF EXISTS data.v_connectivity_index_by_asn CASCADE;
DROP VIEW IF EXISTS data.v_asn_with_neighbours CASCADE;
DROP VIEW IF EXISTS data.v_asn_neighbour CASCADE;

-- Drop v_data_overview and recreate - it references asn_neighbour
DROP VIEW IF EXISTS data.v_data_overview CASCADE;

-- Drop old table
DROP TABLE IF EXISTS data.asn_neighbour CASCADE;
DROP SEQUENCE IF EXISTS data."asn_neighbour_an_id_seq" CASCADE;

-- Create new asn_neighbour_count table
CREATE TABLE data.asn_neighbour_count (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    anc_id integer NOT NULL,
    anc_asn bigint NOT NULL,
    anc_country_iso2 character varying(2) NOT NULL,
    anc_date timestamp without time zone NOT NULL,
    anc_total_neighbours integer NOT NULL,
    anc_local_neighbours integer NOT NULL,
    anc_foreign_neighbours integer NOT NULL,
    load_id integer
);

CREATE SEQUENCE data.asn_neighbour_count_anc_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE data.asn_neighbour_count_anc_id_seq OWNER TO ozi;
ALTER SEQUENCE data.asn_neighbour_count_anc_id_seq OWNED BY data.asn_neighbour_count.anc_id;

ALTER TABLE data.asn_neighbour_count OWNER TO ozi;
ALTER TABLE ONLY data.asn_neighbour_count ALTER COLUMN anc_id SET DEFAULT nextval('data.asn_neighbour_count_anc_id_seq'::regclass);
ALTER TABLE ONLY data.asn_neighbour_count ADD CONSTRAINT asn_neighbour_count_pkey PRIMARY KEY (anc_id);
ALTER TABLE ONLY data.asn_neighbour_count ADD CONSTRAINT asn_neighbour_count_load_id_fkey FOREIGN KEY (load_id) REFERENCES data.etl_load(load_id);

CREATE UNIQUE INDEX idx_asn_neighbour_count_unique ON data.asn_neighbour_count (anc_asn, anc_country_iso2, anc_date);
CREATE INDEX idx_asn_neighbour_count_country_date ON data.asn_neighbour_count (anc_country_iso2, anc_date);

CREATE TRIGGER trigger_set_timestamps_asn_neighbour_count
    BEFORE INSERT OR UPDATE ON data.asn_neighbour_count
    FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();

-- Recreate views that read from asn_neighbour_count
CREATE VIEW data.v_connectivity_index_by_asn AS
 SELECT anc_asn AS an_asn,
    anc_date AS an_date,
    anc_country_iso2 AS asn_country,
    anc_foreign_neighbours AS foreign_neighbours,
    anc_local_neighbours AS local_neighbours,
    anc_total_neighbours AS total_neighbours,
    CASE
        WHEN anc_total_neighbours > 0 THEN (anc_foreign_neighbours::double precision / anc_total_neighbours::double precision)
        ELSE 0::double precision
    END AS foreign_neighbours_share
   FROM data.asn_neighbour_count;

ALTER VIEW data.v_connectivity_index_by_asn OWNER TO ozi;

CREATE VIEW data.v_connectivity_index_by_asn_top10 AS
 SELECT an_asn,
    an_date,
    asn_country,
    foreign_neighbours,
    local_neighbours,
    total_neighbours,
    foreign_neighbours_share,
    rn
   FROM ( SELECT v_connectivity_index_by_asn.an_asn,
            v_connectivity_index_by_asn.an_date,
            v_connectivity_index_by_asn.asn_country,
            v_connectivity_index_by_asn.foreign_neighbours,
            v_connectivity_index_by_asn.local_neighbours,
            v_connectivity_index_by_asn.total_neighbours,
            v_connectivity_index_by_asn.foreign_neighbours_share,
            row_number() OVER (PARTITION BY v_connectivity_index_by_asn.asn_country, v_connectivity_index_by_asn.an_date ORDER BY v_connectivity_index_by_asn.total_neighbours DESC) AS rn
           FROM data.v_connectivity_index_by_asn) sub
  WHERE (rn <= 10);

ALTER VIEW data.v_connectivity_index_by_asn_top10 OWNER TO ozi;

CREATE VIEW data.v_connectivity_index_by_country AS
 SELECT anc_country_iso2 AS asn_country,
    anc_date AS date,
    count(DISTINCT anc_asn) AS asn_count,
    sum(anc_foreign_neighbours) AS foreign_neighbours,
    sum(anc_local_neighbours) AS local_neighbours,
    sum(anc_total_neighbours) AS total_neighbours,
    CASE
        WHEN sum(anc_total_neighbours) > 0 THEN (sum(anc_foreign_neighbours)::double precision / sum(anc_total_neighbours)::double precision)
        ELSE 0::double precision
    END AS foreign_neighbours_share
   FROM data.asn_neighbour_count
  GROUP BY anc_country_iso2, anc_date;

ALTER VIEW data.v_connectivity_index_by_country OWNER TO ozi;

CREATE VIEW data.v_connectivity_index_distinct AS
 SELECT anc_country_iso2 AS asn_country,
    anc_date AS date,
    count(DISTINCT anc_asn) AS asn_count,
    sum(anc_foreign_neighbours) AS foreign_neighbours,
    sum(anc_local_neighbours) AS local_neighbours,
    sum(anc_total_neighbours) AS total_neighbours,
    round(CASE
        WHEN sum(anc_total_neighbours) > 0 THEN (sum(anc_foreign_neighbours)::double precision / sum(anc_total_neighbours)::double precision * 100::double precision)
        ELSE 0::double precision
    END) AS foreign_share_pct
   FROM data.asn_neighbour_count
  GROUP BY anc_country_iso2, anc_date;

ALTER VIEW data.v_connectivity_index_distinct OWNER TO ozi;

CREATE VIEW data.v_asn_with_neighbours AS
 WITH asn_with_neighbours AS (
         SELECT asn.a_id,
            asn.a_date,
            asn.a_country_iso2,
            (EXISTS ( SELECT 1
                   FROM data.asn_neighbour_count
                  WHERE ((asn_neighbour_count.anc_asn = asn.a_ripe_id) AND (asn_neighbour_count.anc_country_iso2 = asn.a_country_iso2) AND (asn_neighbour_count.anc_date = asn.a_date)))) AS has_neighbours
           FROM data.asn
        )
 SELECT a_country_iso2,
    a_date,
    count(*) AS total_asns,
    count(has_neighbours) AS asns_with_neighbours,
    ((count(has_neighbours))::double precision / (count(*))::double precision) AS share_asns_with_neighbours
   FROM asn_with_neighbours
  GROUP BY a_country_iso2, a_date;

ALTER VIEW data.v_asn_with_neighbours OWNER TO ozi;

-- Recreate materialized views
CREATE MATERIALIZED VIEW data.vm_connectivity_index_by_asn_top10 AS
 SELECT an_asn,
    an_date,
    asn_country,
    foreign_neighbours,
    local_neighbours,
    total_neighbours,
    foreign_neighbours_share,
    rn
   FROM data.v_connectivity_index_by_asn_top10
  WITH NO DATA;

ALTER MATERIALIZED VIEW data.vm_connectivity_index_by_asn_top10 OWNER TO ozi;

CREATE MATERIALIZED VIEW data.vm_connectivity_index_by_country AS
 SELECT asn_country,
    date,
    asn_count,
    foreign_neighbours,
    local_neighbours,
    total_neighbours,
    foreign_neighbours_share
   FROM data.v_connectivity_index_by_country
  WITH NO DATA;

ALTER MATERIALIZED VIEW data.vm_connectivity_index_by_country OWNER TO ozi;

-- Recreate v_data_overview (use asn_neighbour_count instead of asn_neighbour)
CREATE VIEW data.v_data_overview AS
 WITH dates AS (
         SELECT generate_series(
            (SELECT min(a.a_date)::timestamp without time zone
               FROM data.asn a),
            (SELECT max(a.a_date)::timestamp without time zone
               FROM data.asn a),
            '1 day'::interval)::date AS date
        ),
 countries AS (
         SELECT c_iso2 AS country_iso2
           FROM data.country
        )
 SELECT d.date,
    c.country_iso2,
    CASE
        WHEN (a.cnt > 0) THEN true
        ELSE false
    END AS has_asn_records,
    CASE
        WHEN (n.cnt > 0) THEN true
        ELSE false
    END AS has_neighbour_records,
    CASE
        WHEN (q.cnt > 0) THEN true
        ELSE false
    END AS has_quality_records,
    CASE
        WHEN (cs.cnt > 0) THEN true
        ELSE false
    END AS has_country_stat_records,
    CASE
        WHEN (ct.cnt > 0) THEN true
        ELSE false
    END AS has_country_traffic_records
   FROM ((((((dates d
     CROSS JOIN countries c)
     LEFT JOIN ( SELECT asn.a_date,
            count(*) AS cnt
           FROM data.asn
          GROUP BY asn.a_date) a ON ((d.date = a.a_date)))
     LEFT JOIN ( SELECT asn_neighbour_count.anc_date,
            count(*) AS cnt
           FROM data.asn_neighbour_count
          GROUP BY asn_neighbour_count.anc_date) n ON ((d.date = n.anc_date)))
     LEFT JOIN ( SELECT country_internet_quality.ci_date,
            country_internet_quality.ci_country_iso2,
            count(*) AS cnt
           FROM data.country_internet_quality
          GROUP BY country_internet_quality.ci_date, country_internet_quality.ci_country_iso2) q ON (((d.date = q.ci_date) AND ((c.country_iso2)::text = (q.ci_country_iso2)::text))))
     LEFT JOIN ( SELECT (country_stat.cs_stats_timestamp)::date AS cs_stats_timestamp,
            country_stat.cs_country_iso2,
            count(*) AS cnt
           FROM data.country_stat
          GROUP BY ((country_stat.cs_stats_timestamp)::date), country_stat.cs_country_iso2) cs ON (((d.date = cs.cs_stats_timestamp) AND ((c.country_iso2)::text = (cs.cs_country_iso2)::text))))
     LEFT JOIN ( SELECT country_traffic.cr_date,
            country_traffic.cr_country_iso2,
            count(*) AS cnt
           FROM data.country_traffic
          GROUP BY country_traffic.cr_date, country_traffic.cr_country_iso2) ct ON (((d.date = ct.cr_date) AND ((c.country_iso2)::text = (ct.cr_country_iso2)::text))))
  ORDER BY d.date, c.country_iso2;

ALTER VIEW data.v_data_overview OWNER TO ozi;

-- Re-grant permissions
GRANT SELECT ON data.v_connectivity_index_by_asn TO looker_user;
GRANT SELECT ON data.v_connectivity_index_by_asn_top10 TO looker_user;
GRANT SELECT ON data.v_connectivity_index_by_country TO looker_user;
