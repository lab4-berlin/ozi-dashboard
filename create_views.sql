\connect ozi_db2
-- Connectivity views now read from asn_neighbour_count (aggregated counts)
CREATE OR REPLACE VIEW data.v_connectivity_index_by_asn AS
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

CREATE OR REPLACE VIEW data.v_connectivity_index_distinct AS
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

GRANT SELECT ON data.v_connectivity_index_by_country TO looker_user;
