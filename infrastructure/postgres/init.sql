-- JARVIS — Aliyar Solutions — PostgreSQL Bootstrap
-- SQLAlchemy creates tables on first run; this file handles extensions + hardening

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Performance indexes created after SQLAlchemy auto-creates tables
-- These run idempotently on every startup (CREATE INDEX IF NOT EXISTS)

-- We use a startup trigger function to add indexes after tables exist
CREATE OR REPLACE FUNCTION create_jarvis_indexes() RETURNS void LANGUAGE plpgsql AS $$
BEGIN
    -- Conversations
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'conversations') THEN
        CREATE INDEX IF NOT EXISTS idx_conv_session  ON conversations (session_id);
        CREATE INDEX IF NOT EXISTS idx_conv_created  ON conversations (created_at DESC);
    END IF;

    -- Approvals
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'approval_requests') THEN
        CREATE INDEX IF NOT EXISTS idx_appr_status   ON approval_requests (status);
        CREATE INDEX IF NOT EXISTS idx_appr_created  ON approval_requests (created_at DESC);
    END IF;

    -- Leads
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'leads') THEN
        CREATE INDEX IF NOT EXISTS idx_leads_status  ON leads (status);
        CREATE INDEX IF NOT EXISTS idx_leads_country ON leads (country);
    END IF;
END;
$$;

-- Create a healthcheck table so pg_isready has something to query
CREATE TABLE IF NOT EXISTS _healthcheck (id SERIAL PRIMARY KEY, ts TIMESTAMP DEFAULT NOW());
INSERT INTO _healthcheck (ts) VALUES (NOW()) ON CONFLICT DO NOTHING;
