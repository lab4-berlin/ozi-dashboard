--
-- PostgreSQL database dump
--

-- Dumped from database version 14.15 (Ubuntu 14.15-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.15 (Ubuntu 14.15-0ubuntu0.22.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: ozi; Type: DATABASE; Schema: -; Owner: -
--

CREATE DATABASE ozi WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE = 'en_US.UTF-8';


\connect ozi

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: data; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA data;


--
-- Name: source; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA source;


--
-- Name: set_timestamps(); Type: FUNCTION; Schema: data; Owner: -
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


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: asn; Type: TABLE; Schema: data; Owner: -
--

CREATE TABLE data.asn (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    a_id integer NOT NULL,
    a_date timestamp without time zone NOT NULL,
    a_country_iso2 character varying(2) NOT NULL,
    a_ripe_id integer NOT NULL,
    a_is_routed boolean NOT NULL
);


--
-- Name: asn_a_id_seq; Type: SEQUENCE; Schema: data; Owner: -
--

CREATE SEQUENCE data.asn_a_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asn_a_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: -
--

ALTER SEQUENCE data.asn_a_id_seq OWNED BY data.asn.a_id;


--
-- Name: asn_neighbour; Type: TABLE; Schema: data; Owner: -
--

CREATE TABLE data.asn_neighbour (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    an_asn integer NOT NULL,
    an_neighbour integer NOT NULL,
    an_date timestamp without time zone NOT NULL,
    an_type character varying(32) NOT NULL,
    an_power integer NOT NULL,
    an_v4_peers integer,
    an_v6_peers integer
);


--
-- Name: country; Type: TABLE; Schema: data; Owner: -
--

CREATE TABLE data.country (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    c_id integer NOT NULL,
    c_iso2 character varying(2) NOT NULL,
    c_name character varying(256) NOT NULL
);


--
-- Name: country_c_id_seq; Type: SEQUENCE; Schema: data; Owner: -
--

CREATE SEQUENCE data.country_c_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_c_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: -
--

ALTER SEQUENCE data.country_c_id_seq OWNED BY data.country.c_id;


--
-- Name: country_internet_quality; Type: TABLE; Schema: data; Owner: -
--

CREATE TABLE data.country_internet_quality (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ci_id integer NOT NULL,
    ci_country_iso2 character varying(2) NOT NULL,
    ci_date timestamp without time zone NOT NULL,
    ci_p75 numeric NOT NULL,
    ci_p50 numeric NOT NULL,
    ci_p25 numeric NOT NULL
);


--
-- Name: country_internet_quality_ci_id_seq; Type: SEQUENCE; Schema: data; Owner: -
--

CREATE SEQUENCE data.country_internet_quality_ci_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_internet_quality_ci_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: -
--

ALTER SEQUENCE data.country_internet_quality_ci_id_seq OWNED BY data.country_internet_quality.ci_id;


--
-- Name: country_stat; Type: TABLE; Schema: data; Owner: -
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
    cs_asns_stats integer
);


--
-- Name: country_stat_cs_id_seq; Type: SEQUENCE; Schema: data; Owner: -
--

CREATE SEQUENCE data.country_stat_cs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_stat_cs_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: -
--

ALTER SEQUENCE data.country_stat_cs_id_seq OWNED BY data.country_stat.cs_id;


--
-- Name: country_tag; Type: TABLE; Schema: data; Owner: -
--

CREATE TABLE data.country_tag (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ct_tag character varying(32) NOT NULL,
    ct_country_id integer NOT NULL
);


--
-- Name: country_traffic; Type: TABLE; Schema: data; Owner: -
--

CREATE TABLE data.country_traffic (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    cr_id integer NOT NULL,
    cr_country_iso2 character varying(2) NOT NULL,
    cr_date timestamp without time zone NOT NULL,
    cr_traffic numeric NOT NULL
);


--
-- Name: country_traffic_cr_id_seq; Type: SEQUENCE; Schema: data; Owner: -
--

CREATE SEQUENCE data.country_traffic_cr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: country_traffic_cr_id_seq; Type: SEQUENCE OWNED BY; Schema: data; Owner: -
--

ALTER SEQUENCE data.country_traffic_cr_id_seq OWNED BY data.country_traffic.cr_id;


--
-- Name: v_country_stat_1d; Type: VIEW; Schema: data; Owner: -
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


--
-- Name: v_country_stat_5m; Type: VIEW; Schema: data; Owner: -
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


--
-- Name: v_country_stat_last; Type: VIEW; Schema: data; Owner: -
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


--
-- Name: v_current_asn; Type: VIEW; Schema: data; Owner: -
--

CREATE VIEW data.v_current_asn AS
 WITH current_asn AS (
         SELECT asn_1.a_ripe_id AS asn_id,
            max(COALESCE(asn_1.a_date, (CURRENT_DATE)::timestamp without time zone)) AS last_updated
           FROM data.asn asn_1
          GROUP BY asn_1.a_ripe_id
        )
 SELECT current_asn.asn_id,
    current_asn.last_updated,
    asn.a_country_iso2 AS asn_country,
    asn.a_is_routed AS is_routed
   FROM (data.asn
     JOIN current_asn ON (((current_asn.asn_id = asn.a_id) AND (current_asn.last_updated = COALESCE(asn.a_date, (CURRENT_DATE)::timestamp without time zone)))));


--
-- Name: api_response; Type: TABLE; Schema: source; Owner: -
--

CREATE TABLE source.api_response (
    created timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ar_id integer NOT NULL,
    ar_url character varying,
    ar_params character varying,
    r_response jsonb
);


--
-- Name: api_response_ar_id_seq; Type: SEQUENCE; Schema: source; Owner: -
--

CREATE SEQUENCE source.api_response_ar_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: api_response_ar_id_seq; Type: SEQUENCE OWNED BY; Schema: source; Owner: -
--

ALTER SEQUENCE source.api_response_ar_id_seq OWNED BY source.api_response.ar_id;


--
-- Name: asn a_id; Type: DEFAULT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.asn ALTER COLUMN a_id SET DEFAULT nextval('data.asn_a_id_seq'::regclass);


--
-- Name: country c_id; Type: DEFAULT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country ALTER COLUMN c_id SET DEFAULT nextval('data.country_c_id_seq'::regclass);


--
-- Name: country_internet_quality ci_id; Type: DEFAULT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_internet_quality ALTER COLUMN ci_id SET DEFAULT nextval('data.country_internet_quality_ci_id_seq'::regclass);


--
-- Name: country_stat cs_id; Type: DEFAULT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_stat ALTER COLUMN cs_id SET DEFAULT nextval('data.country_stat_cs_id_seq'::regclass);


--
-- Name: country_traffic cr_id; Type: DEFAULT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_traffic ALTER COLUMN cr_id SET DEFAULT nextval('data.country_traffic_cr_id_seq'::regclass);


--
-- Name: api_response ar_id; Type: DEFAULT; Schema: source; Owner: -
--

ALTER TABLE ONLY source.api_response ALTER COLUMN ar_id SET DEFAULT nextval('source.api_response_ar_id_seq'::regclass);


--
-- Name: asn asn_pkey; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.asn
    ADD CONSTRAINT asn_pkey PRIMARY KEY (a_id);


--
-- Name: country_internet_quality country_internet_quality_pkey; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_internet_quality
    ADD CONSTRAINT country_internet_quality_pkey PRIMARY KEY (ci_id);


--
-- Name: country country_pkey; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country
    ADD CONSTRAINT country_pkey PRIMARY KEY (c_id);


--
-- Name: country_stat country_stat_pkey; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_stat
    ADD CONSTRAINT country_stat_pkey PRIMARY KEY (cs_id);


--
-- Name: country_tag country_tag_pkey; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_tag
    ADD CONSTRAINT country_tag_pkey PRIMARY KEY (ct_tag, ct_country_id);


--
-- Name: country_traffic country_traffic_pkey; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_traffic
    ADD CONSTRAINT country_traffic_pkey PRIMARY KEY (cr_id);


--
-- Name: asn_neighbour pk_asn_neighbours; Type: CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.asn_neighbour
    ADD CONSTRAINT pk_asn_neighbours PRIMARY KEY (an_asn, an_neighbour, an_type);


--
-- Name: api_response api_response_pkey; Type: CONSTRAINT; Schema: source; Owner: -
--

ALTER TABLE ONLY source.api_response
    ADD CONSTRAINT api_response_pkey PRIMARY KEY (ar_id);


--
-- Name: idx_asn_country; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_country ON data.asn USING btree (a_country_iso2);


--
-- Name: idx_asn_date; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_date ON data.asn USING btree (a_date);


--
-- Name: idx_asn_neighbour_asn; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_neighbour_asn ON data.asn_neighbour USING btree (an_asn);


--
-- Name: idx_asn_neighbour_asn_date; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_neighbour_asn_date ON data.asn_neighbour USING btree (an_asn, an_date);


--
-- Name: idx_asn_neighbour_asn_neighbour_type; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_neighbour_asn_neighbour_type ON data.asn_neighbour USING btree (an_asn, an_neighbour, an_type);


--
-- Name: idx_asn_neighbour_date; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_neighbour_date ON data.asn_neighbour USING btree (an_date);


--
-- Name: idx_asn_neighbour_neighbour; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_neighbour_neighbour ON data.asn_neighbour USING btree (an_neighbour);


--
-- Name: idx_asn_neighbour_type; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_neighbour_type ON data.asn_neighbour USING btree (an_type);


--
-- Name: idx_asn_ripe_id; Type: INDEX; Schema: data; Owner: -
--

CREATE INDEX idx_asn_ripe_id ON data.asn USING btree (a_ripe_id);


--
-- Name: asn trigger_set_timestamps_asn; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_asn BEFORE INSERT OR UPDATE ON data.asn FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: asn_neighbour trigger_set_timestamps_asn_neighbour; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_asn_neighbour BEFORE INSERT OR UPDATE ON data.asn_neighbour FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country trigger_set_timestamps_country; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_country BEFORE INSERT OR UPDATE ON data.country FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_internet_quality trigger_set_timestamps_country_internet_quality; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_country_internet_quality BEFORE INSERT OR UPDATE ON data.country_internet_quality FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_stat trigger_set_timestamps_country_stat; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_country_stat BEFORE INSERT OR UPDATE ON data.country_stat FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_tag trigger_set_timestamps_country_tag; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_country_tag BEFORE INSERT OR UPDATE ON data.country_tag FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_traffic trigger_set_timestamps_country_traffic; Type: TRIGGER; Schema: data; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_country_traffic BEFORE INSERT OR UPDATE ON data.country_traffic FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: api_response trigger_set_timestamps_api_response; Type: TRIGGER; Schema: source; Owner: -
--

CREATE TRIGGER trigger_set_timestamps_api_response BEFORE INSERT OR UPDATE ON source.api_response FOR EACH ROW EXECUTE FUNCTION data.set_timestamps();


--
-- Name: country_tag country_tag_ct_country_id_fkey; Type: FK CONSTRAINT; Schema: data; Owner: -
--

ALTER TABLE ONLY data.country_tag
    ADD CONSTRAINT country_tag_ct_country_id_fkey FOREIGN KEY (ct_country_id) REFERENCES data.country(c_id) ON DELETE CASCADE;


--
-- Name: DATABASE ozi; Type: ACL; Schema: -; Owner: -
--

GRANT ALL ON DATABASE ozi TO ozi;


--
-- PostgreSQL database dump complete
--

