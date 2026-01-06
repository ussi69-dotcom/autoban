-- PostgreSQL initialization script for AutoBan
-- This script runs when the database container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE task_status AS ENUM (
        'backlog',
        'todo',
        'in_progress',
        'in_review',
        'done',
        'cancelled'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE task_priority AS ENUM (
        'low',
        'medium',
        'high',
        'urgent'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE agent_status AS ENUM (
        'initializing',
        'idle',
        'busy',
        'error',
        'stopping',
        'stopped'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant privileges to the autoban user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO autoban;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO autoban;
GRANT USAGE ON SCHEMA public TO autoban;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO autoban;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO autoban;

-- Create helper function for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'AutoBan database initialized successfully';
END $$;
