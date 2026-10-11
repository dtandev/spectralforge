-- SpectralForge's own schema — logically separate from SpectralHub's `public` schema so
-- generated/synthetic data never collides with or requires migrating SpectralHub's tables.
-- SpectralForge READS source spectra via spectralhub.SpectralDatabase (public schema) and
-- WRITES generated spectra + provenance here.
--
-- Design rationale: see docs/Schema_bazy_danych_SpectralForge.md, Section 3.
-- Safe to run against either a local dev DB (after 001_spectralhub_reconstructed.sql) or
-- the real Azure DB (adds a new schema alongside the existing SpectralHub tables, touches
-- nothing that already exists there).

CREATE SCHEMA IF NOT EXISTS spectralforge;

-- One row per augmentation-operator invocation (a specific parameter draw).
CREATE TABLE IF NOT EXISTS spectralforge.operator_runs (
    run_id            SERIAL PRIMARY KEY,
    operator_code     TEXT NOT NULL,        -- 'B1'..'B8', 'unmixing', 'grain_series', 'n_endmember', ...
    operator_version  TEXT,                 -- package version / git commit, for reproducibility
    parameters        JSONB NOT NULL,       -- e.g. {"theta_i": 12.4, "theta_ref": 0} — shape varies per operator
    dataset_batch     TEXT,                 -- named experiment/dataset, e.g. 'ablation_B1_v1'
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    guardrail_passed  BOOLEAN,
    guardrail_notes   TEXT
);

CREATE INDEX IF NOT EXISTS idx_operator_runs_operator_code ON spectralforge.operator_runs (operator_code);
CREATE INDEX IF NOT EXISTS idx_operator_runs_dataset_batch ON spectralforge.operator_runs (dataset_batch);

-- Generated/synthetic spectra themselves.
CREATE TABLE IF NOT EXISTS spectralforge.generated_spectra (
    spectrum_id       SERIAL PRIMARY KEY,
    run_id            INTEGER NOT NULL REFERENCES spectralforge.operator_runs(run_id),
    mineral_class     TEXT,                 -- denormalized label, convenient for ML consumption
    xunit             TEXT NOT NULL,
    yunit             TEXT NOT NULL,
    band_centers      FLOAT8[] NOT NULL,    -- native array — no manual BYTEA encode/decode needed
    reflectance       FLOAT8[] NOT NULL,
    minwavelength     REAL,
    maxwavelength     REAL,
    numvalues         INTEGER,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_generated_spectra_run_id ON spectralforge.generated_spectra (run_id);
CREATE INDEX IF NOT EXISTS idx_generated_spectra_mineral_class ON spectralforge.generated_spectra (mineral_class);

-- N:M — which source spectrum/spectra (and with what weight/fraction) fed into a generated
-- spectrum. weight=1.0 for single-spectrum operators (B1-B5); multiple rows summing to 1 for
-- mixtures (B6/B7/N-endmember, Section 4.3.4 of the research plan).
--
-- NOTE: source_spectrum_id/source_db_alias point into SpectralHub's dynamically-named
-- {alias}_spectra tables. Postgres cannot express a FK to a runtime-chosen table, so this
-- reference is NOT enforced at the database level — validate at the application layer before
-- inserting (check the row exists in {source_db_alias}_spectra first).
CREATE TABLE IF NOT EXISTS spectralforge.generation_inputs (
    generated_spectrum_id  INTEGER NOT NULL REFERENCES spectralforge.generated_spectra(spectrum_id),
    source_db_alias        TEXT NOT NULL DEFAULT '',  -- e.g. 'splib07b'; '' means default ecostress-lib tables
                                                       -- (empty string, not NULL — NULL can't be part of a PRIMARY KEY)
    source_spectrum_id     INTEGER NOT NULL, -- {source_db_alias}_spectra.spectrumid (unenforced FK, see above)
    weight                 FLOAT8 NOT NULL DEFAULT 1.0,
    grain_size_um          FLOAT8,           -- Hapke grain-size series (research plan Section 4.3.3)
    PRIMARY KEY (generated_spectrum_id, source_db_alias, source_spectrum_id)
);
