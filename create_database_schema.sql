--
-- PostgreSQL database cluster dump
--

SET default_transaction_read_only = off;

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

--
-- Roles
--

CREATE ROLE looker_user;
ALTER ROLE looker_user WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD 'SCRAM-SHA-256$4096:084y9kDxKB+HxiD6n7kvXQ==$1aooS1GT49gCRRLYYlq0ttPfk5zd60cc6QUI5uUGN1I=:YgP58xwfMOrXNVvv1o2VyNqwt9NYm+kzlQMTKcElr/I=';
CREATE ROLE ozi;
\set ozi_password `echo "$POSTGRES_OZI_PASSWORD"`
ALTER ROLE ozi WITH NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS PASSWORD :'ozi_password';
--
-- User Configurations
--








--
-- PostgreSQL database cluster dump complete
--

--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4 (Ubuntu 17.4-1.pgdg24.04+2)
-- Dumped by pg_dump version 17.4 (Ubuntu 17.4-1.pgdg24.04+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: ozi_db2; Type: DATABASE; Schema: -; Owner: postgres
--

CREATE DATABASE ozi_db2 WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'en_US.UTF-8';


ALTER DATABASE ozi_db2 OWNER TO postgres;

\connect ozi_db2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: data; Type: SCHEMA; Schema: -; Owner: ozi
--

CREATE SCHEMA data;


ALTER SCHEMA data OWNER TO ozi;

--
-- Name: source; Type: SCHEMA; Schema: -; Owner: ozi
--

CREATE SCHEMA source;


ALTER SCHEMA source OWNER TO ozi;

--
-- Name: set_timestamps(); Type: FUNCTION; Schema: data; Owner: ozi
--

CREATE FUNCTION data.set_timestamps() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        NEW.created := CURRENT_TIMESTAMP;
    END IF;
    NEW.updated := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION data.set_timestamps() OWNER TO ozi;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: asn; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.asn (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    a_id integer NOT NULL,
    a_date timestamp without time zone NOT NULL,
    a_country_iso2 character varying(2) NOT NULL,
    a_ripe_id integer NOT NULL,
    a_is_routed boolean NOT NULL,
    load_id integer
);


ALTER TABLE data.asn OWNER TO ozi;

--
-- Name: asn_a_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data.asn_a_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data.asn_a_id_seq OWNER TO ozi;

--
-- Name: asn_a_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data.asn_a_id_seq OWNED BY data.asn.a_id;


--
-- Name: asn_neighbour; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.asn_neighbour (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    "an_id" integer NOT NULL,
    an_asn bigint NOT NULL,
    an_neighbour bigint NOT NULL,
    an_date timestamp without time zone NOT NULL,
    an_type character varying(32),
    an_power integer NOT NULL,
    an_v4_peers integer,
    an_v6_peers integer,
    load_id integer
);


ALTER TABLE data.asn_neighbour OWNER TO ozi;

--
-- Name: asn_neighbour_an_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data."asn_neighbour_an_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data."asn_neighbour_an_id_seq" OWNER TO ozi;

--
-- Name: asn_neighbour_an_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data."asn_neighbour_an_id_seq" OWNED BY data.asn_neighbour."an_id";


--
-- Name: country; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.country (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    c_id integer NOT NULL,
    c_iso2 character varying(2) NOT NULL,
    c_name character varying(256) NOT NULL,
    c_name_ru character varying(256) NOT NULL
);


ALTER TABLE data.country OWNER TO ozi;

--
-- Name: country_c_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data.country_c_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data.country_c_id_seq OWNER TO ozi;

--
-- Name: country_c_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data.country_c_id_seq OWNED BY data.country.c_id;


--
-- Name: country_internet_quality; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.country_internet_quality (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ci_id integer NOT NULL,
    ci_country_iso2 character varying(2) NOT NULL,
    ci_date timestamp without time zone NOT NULL,
    ci_p75 numeric NOT NULL,
    ci_p50 numeric NOT NULL,
    ci_p25 numeric NOT NULL,
    load_id integer
);


ALTER TABLE data.country_internet_quality OWNER TO ozi;

--
-- Name: country_internet_quality_ci_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data.country_internet_quality_ci_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data.country_internet_quality_ci_id_seq OWNER TO ozi;

--
-- Name: country_internet_quality_ci_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data.country_internet_quality_ci_id_seq OWNED BY data.country_internet_quality.ci_id;


--
-- Name: country_stat; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.country_stat (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    cs_id integer NOT NULL,
    cs_country_iso2 character varying(2) NOT NULL,
    cs_stats_timestamp timestamp without time zone NOT NULL,
    cs_stats_resolution character varying(4) NOT NULL,
    cs_v4_prefixes_ris integer,
    cs_v6_prefixes_ris integer,
    cs_asns_ris integer,
    cs_v4_prefixes_stats integer,
    cs_v6_prefixes_stats integer,
    cs_asns_stats integer,
    load_id integer
);


ALTER TABLE data.country_stat OWNER TO ozi;

--
-- Name: country_stat_cs_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data.country_stat_cs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data.country_stat_cs_id_seq OWNER TO ozi;

--
-- Name: country_stat_cs_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data.country_stat_cs_id_seq OWNED BY data.country_stat.cs_id;


--
-- Name: country_tag; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.country_tag (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ct_tag character varying(32) NOT NULL,
    ct_country_id integer NOT NULL
);


ALTER TABLE data.country_tag OWNER TO ozi;

--
-- Name: country_traffic; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.country_traffic (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    cr_id integer NOT NULL,
    cr_country_iso2 character varying(2) NOT NULL,
    cr_date timestamp without time zone NOT NULL,
    cr_traffic numeric NOT NULL,
    load_id integer
);


ALTER TABLE data.country_traffic OWNER TO ozi;

--
-- Name: country_traffic_cr_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data.country_traffic_cr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data.country_traffic_cr_id_seq OWNER TO ozi;

--
-- Name: country_traffic_cr_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data.country_traffic_cr_id_seq OWNED BY data.country_traffic.cr_id;


--
-- Name: etl_load; Type: TABLE; Schema: data; Owner: ozi
--

CREATE TABLE data.etl_load (
    load_id integer NOT NULL,
    start_time timestamp without time zone NOT NULL,
    finish_time timestamp without time zone,
    command text NOT NULL,
    status character varying(20),
    CONSTRAINT etl_load_status_check CHECK (((status)::text = ANY (ARRAY[('running'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text])))
);


ALTER TABLE data.etl_load OWNER TO ozi;

--
-- Name: etl_load_load_id_seq; Type: SEQUENCE; Schema: data; Owner: ozi
--

CREATE SEQUENCE data.etl_load_load_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE data.etl_load_load_id_seq OWNER TO ozi;

--
-- Name: etl_load_load_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: ozi
--

ALTER SEQUENCE data.etl_load_load_id_seq OWNED BY data.etl_load.load_id;


--
-- Name: v_asn_count; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_asn_count AS
 SELECT a_date,
    a_country_iso2,
    count(a_ripe_id) AS asn_count
   FROM data.asn
  GROUP BY a_date, a_country_iso2;


ALTER VIEW data.v_asn_count OWNER TO ozi;

--
-- Name: v_current_asn; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_current_asn AS
 SELECT DISTINCT ON (a_ripe_id) a_ripe_id AS asn_id,
    a_date AS last_updated,
    a_country_iso2 AS asn_country
   FROM data.asn
  ORDER BY a_ripe_id, a_date DESC;


ALTER VIEW data.v_current_asn OWNER TO ozi;

--
-- Name: vm_current_asn; Type: MATERIALIZED VIEW; Schema: data; Owner: ozi
--

CREATE MATERIALIZED VIEW data.vm_current_asn AS
 SELECT asn_id,
    last_updated,
    asn_country
   FROM data.v_current_asn
  WITH NO DATA;


ALTER MATERIALIZED VIEW data.vm_current_asn OWNER TO ozi;

--
-- Name: v_asn_neighbour; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_asn_neighbour AS
 SELECT n.an_date,
    n.an_asn,
    a1.asn_country,
    n.an_neighbour,
    COALESCE(a2.asn_country, 'UNKNOWN'::character varying) AS neighbour_country,
        CASE
            WHEN ((a1.asn_country)::text <> (COALESCE(a2.asn_country, 'UNKNOWN'::character varying))::text) THEN true
            ELSE false
        END AS is_foreign_neighbour,
    n.an_type,
    n.an_power,
    n.an_v4_peers,
    n.an_v6_peers
   FROM ((data.asn_neighbour n
     LEFT JOIN data.vm_current_asn a1 ON ((a1.asn_id = n.an_asn)))
     LEFT JOIN data.vm_current_asn a2 ON ((a2.asn_id = n.an_neighbour)))
  WHERE ((n.an_type)::text = ANY (ARRAY[('left'::character varying)::text, ('right'::character varying)::text]));


ALTER VIEW data.v_asn_neighbour OWNER TO ozi;

--
-- Name: v_asn_with_neighbours; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_asn_with_neighbours AS
 WITH asn_with_neighbours AS (
         SELECT asn.a_id,
            asn.a_date,
            asn.a_country_iso2,
            (EXISTS ( SELECT 1
                   FROM data.asn_neighbour
                  WHERE ((asn_neighbour.an_asn = asn.a_id) AND (asn_neighbour.an_date = asn.a_date)))) AS has_neighbours
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

--
-- Name: v_connectivity_index_by_asn; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_connectivity_index_by_asn AS
 SELECT an_asn,
    an_date,
    asn_country,
    sum(
        CASE
            WHEN is_foreign_neighbour THEN 1
            ELSE 0
        END) AS foreign_neighbour_count,
    sum(
        CASE
            WHEN (NOT is_foreign_neighbour) THEN 1
            ELSE 0
        END) AS local_neighbour_count,
    count(*) AS total_neighbour_count,
    ((sum(
        CASE
            WHEN is_foreign_neighbour THEN 1
            ELSE 0
        END))::double precision / (count(*))::double precision) AS foreign_neighbours_share
   FROM data.v_asn_neighbour
  WHERE (asn_country IS NOT NULL)
  GROUP BY an_asn, an_date, asn_country;


ALTER VIEW data.v_connectivity_index_by_asn OWNER TO ozi;

--
-- Name: v_connectivity_index_by_asn_top10; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_connectivity_index_by_asn_top10 AS
 SELECT an_asn,
    an_date,
    asn_country,
    foreign_neighbour_count,
    local_neighbour_count,
    total_neighbour_count,
    foreign_neighbours_share,
    rn
   FROM ( SELECT v_connectivity_index_by_asn.an_asn,
            v_connectivity_index_by_asn.an_date,
            v_connectivity_index_by_asn.asn_country,
            v_connectivity_index_by_asn.foreign_neighbour_count,
            v_connectivity_index_by_asn.local_neighbour_count,
            v_connectivity_index_by_asn.total_neighbour_count,
            v_connectivity_index_by_asn.foreign_neighbours_share,
            row_number() OVER (PARTITION BY v_connectivity_index_by_asn.asn_country, v_connectivity_index_by_asn.an_date ORDER BY v_connectivity_index_by_asn.total_neighbour_count DESC) AS rn
           FROM data.v_connectivity_index_by_asn) sub
  WHERE (rn <= 10);


ALTER VIEW data.v_connectivity_index_by_asn_top10 OWNER TO ozi;

--
-- Name: v_connectivity_index_by_country; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_connectivity_index_by_country AS
 SELECT asn_country,
    an_date AS date,
    count(DISTINCT an_asn) AS asn_count,
    sum(
        CASE
            WHEN is_foreign_neighbour THEN 1
            ELSE 0
        END) AS foreign_neighbour_count,
    sum(
        CASE
            WHEN (NOT is_foreign_neighbour) THEN 1
            ELSE 0
        END) AS local_neighbour_count,
    count(*) AS total_neighbour_count,
    ((sum(
        CASE
            WHEN is_foreign_neighbour THEN 1
            ELSE 0
        END))::double precision / (count(*))::double precision) AS foreign_neighbours_share
   FROM data.v_asn_neighbour
  WHERE (asn_country IS NOT NULL)
  GROUP BY asn_country, an_date;


ALTER VIEW data.v_connectivity_index_by_country OWNER TO ozi;

--
-- Name: v_connectivity_index_distinct; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_connectivity_index_distinct AS
 SELECT asn_country,
    an_date AS date,
    count(DISTINCT an_asn) AS asn_count,
    sum(
        CASE
            WHEN is_foreign_neighbour THEN 1
            ELSE 0
        END) AS foreign_neighbour_count,
    sum(
        CASE
            WHEN NOT is_foreign_neighbour THEN 1
            ELSE 0
        END) AS local_neighbour_count,
    count(*) AS total_neighbour_count,
    round(sum(
        CASE
            WHEN is_foreign_neighbour THEN 1
            ELSE 0
        END)::double precision / NULLIF(count(*), 0)::double precision * 100::double precision) AS foreign_share_pct
   FROM ( SELECT DISTINCT v_asn_neighbour.an_asn,
            v_asn_neighbour.an_neighbour,
            v_asn_neighbour.an_date,
            v_asn_neighbour.asn_country,
            v_asn_neighbour.is_foreign_neighbour
           FROM data.v_asn_neighbour) deduplicated
  GROUP BY asn_country, an_date;


ALTER VIEW data.v_connectivity_index_distinct OWNER TO ozi;

--
-- Name: v_country_stat_1d; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_country_stat_1d AS
 SELECT country_stat.created,
    country_stat.updated,
    country_stat.cs_id,
    country_stat.cs_country_iso2,
    country_stat.cs_stats_timestamp,
    country_stat.cs_stats_resolution,
    country_stat.cs_v4_prefixes_ris,
    country_stat.cs_v6_prefixes_ris,
    country_stat.cs_asns_ris,
    country_stat.cs_v4_prefixes_stats,
    country_stat.cs_v6_prefixes_stats,
    country_stat.cs_asns_stats,
    country.c_name
   FROM (data.country_stat
     JOIN data.country ON (((country.c_iso2)::text = (country_stat.cs_country_iso2)::text)))
  WHERE ((country_stat.cs_stats_resolution)::text = '1d'::text);


ALTER VIEW data.v_country_stat_1d OWNER TO ozi;

--
-- Name: v_country_stat_5m; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_country_stat_5m AS
 SELECT country_stat.created,
    country_stat.updated,
    country_stat.cs_id,
    country_stat.cs_country_iso2,
    country_stat.cs_stats_timestamp,
    country_stat.cs_stats_resolution,
    country_stat.cs_v4_prefixes_ris,
    country_stat.cs_v6_prefixes_ris,
    country_stat.cs_asns_ris,
    country_stat.cs_v4_prefixes_stats,
    country_stat.cs_v6_prefixes_stats,
    country_stat.cs_asns_stats,
    country.c_name
   FROM (data.country_stat
     JOIN data.country ON (((country.c_iso2)::text = (country_stat.cs_country_iso2)::text)))
  WHERE ((country_stat.cs_stats_resolution)::text = '5m'::text);


ALTER VIEW data.v_country_stat_5m OWNER TO ozi;

--
-- Name: v_country_stat_last; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_country_stat_last AS
 WITH last_dates AS (
         SELECT country_stat_1.cs_country_iso2 AS country,
            max(country_stat_1.cs_stats_timestamp) AS last_date
           FROM data.country_stat country_stat_1
          WHERE ((country_stat_1.cs_stats_resolution)::text = '1d'::text)
          GROUP BY country_stat_1.cs_country_iso2
        )
 SELECT country.c_name,
    country_stat.created,
    country_stat.updated,
    country_stat.cs_id,
    country_stat.cs_country_iso2,
    country_stat.cs_stats_timestamp,
    country_stat.cs_stats_resolution,
    country_stat.cs_v4_prefixes_ris,
    country_stat.cs_v6_prefixes_ris,
    country_stat.cs_asns_ris,
    country_stat.cs_v4_prefixes_stats,
    country_stat.cs_v6_prefixes_stats,
    country_stat.cs_asns_stats
   FROM ((data.country_stat
     JOIN last_dates ON (((last_dates.last_date = country_stat.cs_stats_timestamp) AND ((last_dates.country)::text = (country_stat.cs_country_iso2)::text))))
     JOIN data.country ON (((country.c_iso2)::text = (country_stat.cs_country_iso2)::text)))
  WHERE ((country_stat.cs_stats_resolution)::text = '1d'::text);


ALTER VIEW data.v_country_stat_last OWNER TO ozi;

--
-- Name: v_data_overview; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_data_overview AS
 WITH date_range AS (
         SELECT date_trunc('day'::text, min(asn.a_date)) AS start_date,
            date_trunc('day'::text, max(asn.a_date)) AS end_date
           FROM data.asn
        ), dates AS (
         SELECT generate_series(date_range.start_date, date_range.end_date, '1 day'::interval) AS date
           FROM date_range
        ), countries AS (
         SELECT DISTINCT asn.a_country_iso2 AS country_iso2
           FROM data.asn
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
     LEFT JOIN ( SELECT asn_neighbour.an_date,
            count(*) AS cnt
           FROM data.asn_neighbour
          GROUP BY asn_neighbour.an_date) n ON ((d.date = n.an_date)))
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

--
-- Name: v_neighbours_by_country; Type: VIEW; Schema: data; Owner: ozi
--

CREATE VIEW data.v_neighbours_by_country AS
 SELECT asn_country,
    neighbour_country,
    count(*) AS neighbours_count
   FROM data.v_asn_neighbour
  GROUP BY asn_country, neighbour_country;


ALTER VIEW data.v_neighbours_by_country OWNER TO ozi;

--
-- Name: vm_asn_neighbour; Type: MATERIALIZED VIEW; Schema: data; Owner: ozi
--

CREATE MATERIALIZED VIEW data.vm_asn_neighbour AS
 SELECT an_date,
    an_asn,
    asn_country,
    an_neighbour,
    neighbour_country,
    is_foreign_neighbour,
    an_type,
    an_power,
    an_v4_peers,
    an_v6_peers
   FROM data.v_asn_neighbour
  WITH NO DATA;


ALTER MATERIALIZED VIEW data.vm_asn_neighbour OWNER TO ozi;

--
-- Name: vm_connectivity_index_by_asn_top10; Type: MATERIALIZED VIEW; Schema: data; Owner: ozi
--

CREATE MATERIALIZED VIEW data.vm_connectivity_index_by_asn_top10 AS
 SELECT an_asn,
    an_date,
    asn_country,
    foreign_neighbour_count,
    local_neighbour_count,
    total_neighbour_count,
    foreign_neighbours_share,
    rn
   FROM data.v_connectivity_index_by_asn_top10
  WITH NO DATA;


ALTER MATERIALIZED VIEW data.vm_connectivity_index_by_asn_top10 OWNER TO ozi;

--
-- Name: vm_connectivity_index_by_country; Type: MATERIALIZED VIEW; Schema: data; Owner: ozi
--

CREATE MATERIALIZED VIEW data.vm_connectivity_index_by_country AS
 SELECT asn_country,
    date,
    asn_count,
    foreign_neighbour_count,
    local_neighbour_count,
    total_neighbour_count,
    foreign_neighbours_share
   FROM data.v_connectivity_index_by_country
  WITH NO DATA;


ALTER MATERIALIZED VIEW data.vm_connectivity_index_by_country OWNER TO ozi;

--
-- Name: api_response; Type: TABLE; Schema: source; Owner: ozi
--

CREATE TABLE source.api_response (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ar_id integer NOT NULL,
    ar_url character varying,
    ar_params character varying,
    r_response jsonb
);


ALTER TABLE source.api_response OWNER TO ozi;

--
-- Name: api_response_ar_id_seq; Type: SEQUENCE; Schema: source; Owner: ozi
--

CREATE SEQUENCE source.api_response_ar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE source.api_response_ar_id_seq OWNER TO ozi;

--
-- Name: api_response_ar_id_seq; Type: SEQUENCE OWNED BY; Schema: source; Owner: ozi
--

ALTER SEQUENCE source.api_response_ar_id_seq OWNED BY source.api_response.ar_id;


--
-- Name: asn a_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.asn ALTER COLUMN a_id SET DEFAULT nextval('data.asn_a_id_seq'::regclass);


--
-- Name: asn_neighbour an_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.asn_neighbour ALTER COLUMN "an_id" SET DEFAULT nextval('data."asn_neighbour_an_id_seq"'::regclass);


--
-- Name: country c_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country ALTER COLUMN c_id SET DEFAULT nextval('data.country_c_id_seq'::regclass);


--
-- Name: country_internet_quality ci_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_internet_quality ALTER COLUMN ci_id SET DEFAULT nextval('data.country_internet_quality_ci_id_seq'::regclass);


--
-- Name: country_stat cs_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_stat ALTER COLUMN cs_id SET DEFAULT nextval('data.country_stat_cs_id_seq'::regclass);


--
-- Name: country_traffic cr_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_traffic ALTER COLUMN cr_id SET DEFAULT nextval('data.country_traffic_cr_id_seq'::regclass);


--
-- Name: etl_load load_id; Type: DEFAULT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.etl_load ALTER COLUMN load_id SET DEFAULT nextval('data.etl_load_load_id_seq'::regclass);


--
-- Name: api_response ar_id; Type: DEFAULT; Schema: source; Owner: ozi
--

ALTER TABLE ONLY source.api_response ALTER COLUMN ar_id SET DEFAULT nextval('source.api_response_ar_id_seq'::regclass);


--
-- Name: asn_neighbour asn_neighbour_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.asn_neighbour
    ADD CONSTRAINT asn_neighbour_pkey PRIMARY KEY ("an_id");


--
-- Name: asn asn_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.asn
    ADD CONSTRAINT asn_pkey PRIMARY KEY (a_id);


--
-- Name: country_internet_quality country_internet_quality_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_internet_quality
    ADD CONSTRAINT country_internet_quality_pkey PRIMARY KEY (ci_id);


--
-- Name: country country_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country
    ADD CONSTRAINT country_pkey PRIMARY KEY (c_id);


--
-- Name: country_stat country_stat_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_stat
    ADD CONSTRAINT country_stat_pkey PRIMARY KEY (cs_id);


--
-- Name: country_tag country_tag_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_tag
    ADD CONSTRAINT country_tag_pkey PRIMARY KEY (ct_tag, ct_country_id);


--
-- Name: country_traffic country_traffic_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_traffic
    ADD CONSTRAINT country_traffic_pkey PRIMARY KEY (cr_id);


--
-- Name: etl_load etl_load_pkey; Type: CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.etl_load
    ADD CONSTRAINT etl_load_pkey PRIMARY KEY (load_id);


--
-- Name: api_response api_response_pkey; Type: CONSTRAINT; Schema: source; Owner: ozi
--

ALTER TABLE ONLY source.api_response
    ADD CONSTRAINT api_response_pkey PRIMARY KEY (ar_id);


--
-- Name: idx_asn_country; Type: INDEX; Schema: data; Owner: ozi
--

CREATE INDEX idx_asn_country ON data.asn USING btree (a_country_iso2);


--
-- Name: idx_asn_date; Type: INDEX; Schema: data; Owner: ozi
--

CREATE INDEX idx_asn_date ON data.asn USING btree (a_date);


--
-- Name: idx_asn_ripe_date; Type: INDEX; Schema: data; Owner: ozi
--

CREATE INDEX idx_asn_ripe_date ON data.asn USING btree (a_ripe_id, a_date DESC);


--
-- Name: idx_asn_ripe_id; Type: INDEX; Schema: data; Owner: ozi
--

CREATE INDEX idx_asn_ripe_id ON data.asn USING btree (a_ripe_id);


--
-- Name: asn trigger_set_timestamps_asn; Type: TRIGGER; Schema: data; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_asn BEFORE INSERT OR UPDATE ON data.asn FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country trigger_set_timestamps_country; Type: TRIGGER; Schema: data; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_country BEFORE INSERT OR UPDATE ON data.country FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_internet_quality trigger_set_timestamps_country_internet_quality; Type: TRIGGER; Schema: data; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_country_internet_quality BEFORE INSERT OR UPDATE ON data.country_internet_quality FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_stat trigger_set_timestamps_country_stat; Type: TRIGGER; Schema: data; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_country_stat BEFORE INSERT OR UPDATE ON data.country_stat FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_tag trigger_set_timestamps_country_tag; Type: TRIGGER; Schema: data; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_country_tag BEFORE INSERT OR UPDATE ON data.country_tag FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_traffic trigger_set_timestamps_country_traffic; Type: TRIGGER; Schema: data; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_country_traffic BEFORE INSERT OR UPDATE ON data.country_traffic FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: api_response trigger_set_timestamps_api_response; Type: TRIGGER; Schema: source; Owner: ozi
--

CREATE TRIGGER trigger_set_timestamps_api_response BEFORE INSERT OR UPDATE ON source.api_response FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: asn asn_load_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.asn
    ADD CONSTRAINT asn_load_id_fkey FOREIGN KEY (load_id) REFERENCES data.etl_load(load_id);


--
-- Name: asn_neighbour asn_neighbour_load_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.asn_neighbour
    ADD CONSTRAINT asn_neighbour_load_id_fkey FOREIGN KEY (load_id) REFERENCES data.etl_load(load_id);


--
-- Name: country_internet_quality country_internet_quality_load_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_internet_quality
    ADD CONSTRAINT country_internet_quality_load_id_fkey FOREIGN KEY (load_id) REFERENCES data.etl_load(load_id);


--
-- Name: country_stat country_stat_load_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_stat
    ADD CONSTRAINT country_stat_load_id_fkey FOREIGN KEY (load_id) REFERENCES data.etl_load(load_id);


--
-- Name: country_tag country_tag_ct_country_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_tag
    ADD CONSTRAINT country_tag_ct_country_id_fkey FOREIGN KEY (ct_country_id) REFERENCES data.country(c_id) ON DELETE CASCADE;


--
-- Name: country_traffic country_traffic_load_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: ozi
--

ALTER TABLE ONLY data.country_traffic
    ADD CONSTRAINT country_traffic_load_id_fkey FOREIGN KEY (load_id) REFERENCES data.etl_load(load_id);


--
-- Name: DATABASE ozi_db2; Type: ACL; Schema: -; Owner: postgres
--

GRANT ALL ON DATABASE ozi_db2 TO ozi;


--
-- Name: SCHEMA data; Type: ACL; Schema: -; Owner: ozi
--

GRANT USAGE ON SCHEMA data TO looker_user;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO ozi;


--
-- Name: TABLE asn; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.asn TO looker_user;


--
-- Name: SEQUENCE asn_a_id_seq; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON SEQUENCE data.asn_a_id_seq TO looker_user;


--
-- Name: TABLE country; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.country TO looker_user;


--
-- Name: SEQUENCE country_c_id_seq; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON SEQUENCE data.country_c_id_seq TO looker_user;


--
-- Name: TABLE country_internet_quality; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.country_internet_quality TO looker_user;


--
-- Name: SEQUENCE country_internet_quality_ci_id_seq; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON SEQUENCE data.country_internet_quality_ci_id_seq TO looker_user;


--
-- Name: TABLE country_stat; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.country_stat TO looker_user;


--
-- Name: SEQUENCE country_stat_cs_id_seq; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON SEQUENCE data.country_stat_cs_id_seq TO looker_user;


--
-- Name: TABLE country_tag; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.country_tag TO looker_user;


--
-- Name: TABLE country_traffic; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.country_traffic TO looker_user;


--
-- Name: SEQUENCE country_traffic_cr_id_seq; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON SEQUENCE data.country_traffic_cr_id_seq TO looker_user;


--
-- Name: TABLE v_asn_count; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.v_asn_count TO looker_user;


--
-- Name: TABLE v_connectivity_index_by_asn; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.v_connectivity_index_by_asn TO looker_user;


--
-- Name: TABLE v_connectivity_index_by_asn_top10; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.v_connectivity_index_by_asn_top10 TO looker_user;


--
-- Name: TABLE v_country_stat_1d; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.v_country_stat_1d TO looker_user;


--
-- Name: TABLE v_country_stat_5m; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.v_country_stat_5m TO looker_user;


--
-- Name: TABLE v_country_stat_last; Type: ACL; Schema: data; Owner: ozi
--

GRANT SELECT ON TABLE data.v_country_stat_last TO looker_user;


--
-- Name: TABLE vm_connectivity_index_by_country; Type: ACL; Schema: data; Owner: ozi
--

GRANT ALL ON TABLE data.vm_connectivity_index_by_country TO looker_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: data; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA data GRANT SELECT ON SEQUENCES TO looker_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: data; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA data GRANT SELECT ON TABLES TO looker_user;


--
-- PostgreSQL database dump complete
--

