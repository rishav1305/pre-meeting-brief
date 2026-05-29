-- Phase 4 migrations as raw DDL.
-- Run this against the Neon DB via either:
--   1. Neon Console SQL editor: https://console.neon.tech
--   2. Vercel dashboard → Storage → Postgres → Query
--   3. psql (with network access to Neon)
--
-- This file IS the canonical fallback when alembic upgrade head cannot run
-- from the local network. After running, manually advance the alembic_version
-- row (UPDATE at the bottom) so future migrations re-sync.

BEGIN;

-- ────────────────────────────────────────────────────────────────────
-- 0003_firm_config — firm_config table + seed Renegade as default
-- ────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS firm_config (
    firm_id            UUID PRIMARY KEY,
    name               VARCHAR(128)              NOT NULL,
    thesis_label       VARCHAR(128)              NOT NULL,
    thesis_description TEXT                      NOT NULL,
    fit_rubric         TEXT                      NOT NULL,
    is_default         BOOLEAN                   NOT NULL DEFAULT false,
    created_at         TIMESTAMP WITH TIME ZONE  NOT NULL DEFAULT now()
);

-- Only one default firm at a time
CREATE UNIQUE INDEX IF NOT EXISTS firm_config_one_default
    ON firm_config (is_default)
    WHERE is_default = true;

-- Seed Renegade as the default firm.
-- We use ON CONFLICT DO NOTHING so re-running is safe; a different uuid each
-- time would otherwise insert duplicates. The partial unique index above
-- prevents two defaults but doesn't dedup on name.
INSERT INTO firm_config (firm_id, name, thesis_label, thesis_description, fit_rubric, is_default)
SELECT
    gen_random_uuid(),
    'Renegade Capital',
    'Markets That Matter',
    'Markets That Matter — workflow-critical sectors in defense, dual-use, vertical infrastructure, and industries underserved by SaaS.',
    '5/5 = core thesis (defense, dual-use, workflow-critical vertical infra). 4/5 = strong adjacent (industrial automation, deep-tech infra). 3/5 = AI infra or compute substrate enabling thesis sectors. 2/5 = horizontal SaaS in non-thesis sectors. 1/5 = off-thesis or commodity.',
    true
WHERE NOT EXISTS (SELECT 1 FROM firm_config WHERE is_default = true);


-- ────────────────────────────────────────────────────────────────────
-- 0004_brief_distribution — distribution_log JSONB on pre_meeting_brief
-- ────────────────────────────────────────────────────────────────────

ALTER TABLE pre_meeting_brief
    ADD COLUMN IF NOT EXISTS distribution_log JSONB;


-- ────────────────────────────────────────────────────────────────────
-- Advance alembic_version so future `alembic upgrade head` re-syncs
-- ────────────────────────────────────────────────────────────────────

UPDATE alembic_version SET version_num = '0004_brief_distribution';

COMMIT;

-- Verify after running:
--   SELECT * FROM firm_config;
--   SELECT column_name FROM information_schema.columns
--     WHERE table_name = 'pre_meeting_brief' AND column_name = 'distribution_log';
--   SELECT version_num FROM alembic_version;
