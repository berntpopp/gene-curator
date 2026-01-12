-- System Logs Table for Persistent Log Storage
-- FIX #19: Added partitioning and log rotation strategy

-- Main logs table (partitioned by month)
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    logger TEXT NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}'::JSONB NOT NULL,

    -- Request correlation
    request_id TEXT,

    -- User context
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address TEXT,
    user_agent TEXT,

    -- HTTP context
    path TEXT,
    method TEXT,
    status_code INTEGER,
    duration_ms DOUBLE PRECISION,

    -- Error context
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,

    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create initial partitions (first 3 months)
CREATE TABLE IF NOT EXISTS system_logs_2025_10 PARTITION OF system_logs
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE IF NOT EXISTS system_logs_2025_11 PARTITION OF system_logs
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE IF NOT EXISTS system_logs_2025_12 PARTITION OF system_logs
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Indexes for common queries (applied to all partitions)
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);
CREATE INDEX IF NOT EXISTS idx_system_logs_request_id ON system_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_user_id ON system_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_logger ON system_logs(logger);
CREATE INDEX IF NOT EXISTS idx_system_logs_path ON system_logs(path);

-- JSONB GIN index for efficient context queries
CREATE INDEX IF NOT EXISTS idx_system_logs_context_gin ON system_logs USING GIN (context);

-- Composite index for common queries
CREATE INDEX IF NOT EXISTS idx_system_logs_level_timestamp ON system_logs(level, timestamp DESC);

-- FIX #19: Log retention function (delete logs older than 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS void AS $$
DECLARE
    partition_name TEXT;
    partition_date DATE;
    cutoff_date DATE := CURRENT_DATE - INTERVAL '90 days';
BEGIN
    -- Find and drop partitions older than cutoff
    FOR partition_name, partition_date IN
        SELECT
            tablename,
            to_date(substring(tablename from 'system_logs_(\d{4}_\d{2})'), 'YYYY_MM')
        FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename LIKE 'system_logs_%'
        AND tablename != 'system_logs'
    LOOP
        IF partition_date < cutoff_date THEN
            EXECUTE format('DROP TABLE IF EXISTS %I', partition_name);
            RAISE NOTICE 'Dropped old partition: %', partition_name;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- FIX #19: Function to create next month's partition
CREATE OR REPLACE FUNCTION create_next_log_partition()
RETURNS void AS $$
DECLARE
    next_month DATE := date_trunc('month', CURRENT_DATE + INTERVAL '1 month');
    following_month DATE := date_trunc('month', CURRENT_DATE + INTERVAL '2 months');
    partition_name TEXT := 'system_logs_' || to_char(next_month, 'YYYY_MM');
BEGIN
    -- Check if partition already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables
        WHERE schemaname = 'public'
        AND tablename = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS %I PARTITION OF system_logs FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            next_month,
            following_month
        );
        RAISE NOTICE 'Created partition: %', partition_name;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE system_logs IS 'Unified logging system with monthly partitioning and automatic retention';
COMMENT ON COLUMN system_logs.context IS 'JSONB field for structured logging data - supports rich queries';
COMMENT ON COLUMN system_logs.request_id IS 'Correlation ID for tracking all logs within a single request';
COMMENT ON COLUMN system_logs.duration_ms IS 'Request processing time in milliseconds';

-- Recommended cron jobs (to be added to system crontab):
-- Daily partition creation: 0 0 * * * psql -d gene_curator -c "SELECT create_next_log_partition();"
-- Weekly cleanup: 0 2 * * 0 psql -d gene_curator -c "SELECT cleanup_old_logs();"
