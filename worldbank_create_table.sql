CREATE TABLE IF NOT EXISTS worldbank_country_stats (
    country        VARCHAR(128) NOT NULL,
    country_code   CHAR(3)      NOT NULL,
    year           INT          NOT NULL,
    population     BIGINT,
    gdp_per_capita NUMERIC,
    CONSTRAINT worldbank_country_stats_pk PRIMARY KEY (country_code, year)
);