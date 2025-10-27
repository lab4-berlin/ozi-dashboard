DROP VIEW IF EXISTS vw_country_economics;
DROP TABLE IF EXISTS worldbank_country_stats;

CREATE TABLE IF NOT EXISTS worldbank_country_stats (
    country        VARCHAR(128) NOT NULL,
    country_iso2   CHAR(2),              
    country_code   CHAR(3)      NOT NULL, 
    year           INT          NOT NULL,
    population     BIGINT,
    gdp_per_capita NUMERIC(15,2),
    CONSTRAINT worldbank_country_stats_pk PRIMARY KEY (country_code, year)
);


CREATE OR REPLACE VIEW vw_country_economics AS
SELECT 
    dc.c_iso2,
    dc.c_name,
    dc.c_name_ru,
    w.year,
    w.population,
    ROUND(w.gdp_per_capita, 2) AS gdp_per_capita
FROM data.country dc
LEFT JOIN worldbank_country_stats w
  ON w.country_iso2 = dc.c_iso2;