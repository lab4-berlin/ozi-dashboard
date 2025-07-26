CREATE TABLE IF NOT EXISTS sample_table (
    id SERIAL PRIMARY KEY,
    value INTEGER NOT NULL
);

INSERT INTO sample_table (value) VALUES (10), (20), (30), (40), (50);
