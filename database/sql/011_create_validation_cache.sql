-- Migration 011: Create validation_cache table
-- ClinGen SOP v11 - Cache external validator results (HGNC, PubMed, HPO)
-- Date: 2025-10-14

BEGIN;

-- Create validation_cache table
CREATE TABLE validation_cache (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Validator Info
    validator_name VARCHAR(50) NOT NULL,      -- 'hgnc', 'pubmed', 'hpo'
    input_value VARCHAR(500) NOT NULL,        -- Gene symbol, PMID, HPO term
    validator_input_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 of validator_name + input_value

    -- Validation Result
    is_valid BOOLEAN NOT NULL,
    validation_status VARCHAR(20) NOT NULL,   -- 'valid', 'invalid', 'error', 'not_found'
    validation_response JSONB NOT NULL,
    /*
    {
      "approved_symbol": "BRCA1",        // For HGNC
      "hgnc_id": "HGNC:1100",
      "alias_symbols": ["RNF53"],
      "previous_symbols": [],
      "status": "Approved",

      // OR for PubMed
      "title": "Article title",
      "authors": ["Smith J", "Doe A"],
      "journal": "Nature",
      "year": 2024,
      "doi": "10.1038/...",

      // OR for HPO
      "term_name": "Intellectual disability",
      "definition": "...",
      "synonyms": ["Mental retardation"]
    }
    */

    -- Suggestions (for invalid inputs)
    suggestions JSONB,
    /*
    {
      "did_you_mean": ["BRCA1", "BRCA2"],
      "confidence_scores": [0.95, 0.87]
    }
    */

    -- Error Info
    error_message TEXT,
    error_code VARCHAR(50),

    -- Cache Control
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 1,
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX idx_validation_cache_hash ON validation_cache(validator_input_hash);
CREATE INDEX idx_validation_cache_validator ON validation_cache(validator_name, input_value);
CREATE INDEX idx_validation_cache_expiry ON validation_cache(expires_at);
CREATE INDEX idx_validation_cache_valid ON validation_cache(validator_name, is_valid);

-- Index for expired entries cleanup (for manual cleanup jobs)
CREATE INDEX idx_validation_cache_expired ON validation_cache(expires_at);

COMMENT ON TABLE validation_cache IS 'Cache for external validator results (HGNC, PubMed, HPO) to reduce API calls';
COMMENT ON COLUMN validation_cache.validator_input_hash IS 'SHA256 hash of validator_name + input_value for fast lookups';
COMMENT ON COLUMN validation_cache.expires_at IS 'TTL: HGNC=30d, PubMed=90d, HPO=14d';
COMMENT ON COLUMN validation_cache.access_count IS 'Number of times this cache entry was accessed';

COMMIT;
