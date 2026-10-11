-- Reconstructed (NOT authoritative) SpectralHub schema, derived from static analysis of
-- spectralhub/database.py (SpectralDatabase.create_spectral_db, create_spectral_profiles_table).
-- Purpose: let SpectralForge be developed and tested locally (see db/docker-compose.yml)
-- without needing live network access to the production Azure database ("ecostress-lib").
--
-- TODO: verify this against a real schema snapshot — run scripts/inspect_live_db_schema.py
-- against the live DB and diff the result against this file before treating it as ground
-- truth. Do NOT run this file against the production Azure DB: those tables already exist
-- there and are owned by SpectralHub, not SpectralForge.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Global sensor/profile registry (one table, no per-alias split)
CREATE TABLE IF NOT EXISTS spectral_profiles (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    centers FLOAT8[],
    bandwidths FLOAT8[],
    centers_stdevs FLOAT8[],
    bandwidth_stdevs FLOAT8[],
    band_quantity VARCHAR(50),
    center_units VARCHAR(50)
);

-- Default (unprefixed) tables — per the SpectralHub showcase notebook, these hold the
-- Ecostress library ("Domyślnie wszystkie operacje są wykonywane na bibliotece Ecostress").
CREATE TABLE IF NOT EXISTS samples (
    sampleid SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT,
    class TEXT,
    subclass TEXT,
    particlesize TEXT,
    samplenum TEXT,
    owner TEXT,
    origin TEXT,
    phase TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS spectra (
    spectrumid SERIAL PRIMARY KEY,
    sampleid INTEGER REFERENCES samples(sampleid),
    sensorcalibrationid INTEGER,
    instrument TEXT,
    environment TEXT,
    measurement TEXT,
    xunit TEXT,
    yunit TEXT,
    minwavelength REAL,
    maxwavelength REAL,
    numvalues INTEGER,
    xdata BYTEA NOT NULL,
    ydata BYTEA NOT NULL,
    location geometry(Point, 4326)
);

-- Reusable function mirroring SpectralDatabase.create_spectral_db(db_alias) for any
-- NAMED alias (the default "samples"/"spectra" pair above is the one special case where
-- db_alias is empty/None — see database.py: `f"{db_alias}_spectra" if db_alias else "spectra"`).
CREATE OR REPLACE FUNCTION spectralhub_create_alias_tables(alias text)
RETURNS void AS $$
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I (
            sampleid SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            class TEXT,
            subclass TEXT,
            particlesize TEXT,
            samplenum TEXT,
            owner TEXT,
            origin TEXT,
            phase TEXT,
            description TEXT
        );', alias || '_samples'
    );

    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I (
            spectrumid SERIAL PRIMARY KEY,
            sampleid INTEGER REFERENCES %I(sampleid),
            sensorcalibrationid INTEGER,
            instrument TEXT,
            environment TEXT,
            measurement TEXT,
            xunit TEXT,
            yunit TEXT,
            minwavelength REAL,
            maxwavelength REAL,
            numvalues INTEGER,
            xdata BYTEA NOT NULL,
            ydata BYTEA NOT NULL,
            location geometry(Point, 4326)
        );', alias || '_spectra', alias || '_samples'
    );
END;
$$ LANGUAGE plpgsql;

-- Known aliases observed in the live DB (per examples/spectralhub_showcase.ipynb output of
-- db.get_tables() on 2026-07-12). Row DATA is not reconstructed here, only structure —
-- these tables start empty locally.
SELECT spectralhub_create_alias_tables('splib07b');
SELECT spectralhub_create_alias_tables('Geometric-medians-USGS');
SELECT spectralhub_create_alias_tables('mineral_mixtures_chile_2023');
SELECT spectralhub_create_alias_tables('dt');
