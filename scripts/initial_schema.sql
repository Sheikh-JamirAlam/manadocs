-- Enable vector and uuid-ossp extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Automated updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(512) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    document_type VARCHAR(50) NOT NULL DEFAULT 'unknown', -- 'contract', 'amendment', 'invoice'
    vendor_name VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',          -- 'pending', 'processing', 'processed', 'flagged', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_doc_chunk UNIQUE (document_id, chunk_index)
);


CREATE TABLE IF NOT EXISTS document_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    vendor_name VARCHAR(255),
    client_name VARCHAR(255),
    summary TEXT,
    summary_embedding VECTOR(1536),
    facts JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS rule_violations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES rules(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    citation JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) DEFAULT 'pending',                  -- 'pending', 'resolved'
    resolution VARCHAR(50),                                 -- 'enforce_rule', 'override_rule'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',                  -- 'pending', 'resolved', 'reopened'
    description TEXT,
    active_value JSONB,
    active_source_doc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    conflicting_sources JSONB NOT NULL,
    selected_doc_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    resolution VARCHAR(50),
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS deliverables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    version INT DEFAULT 1,
    index INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR(255) NOT NULL,
    node_name VARCHAR(100) NOT NULL,
    tokens_prompt INT DEFAULT 0,
    tokens_completion INT DEFAULT 0,
    estimated_cost NUMERIC(10, 6) DEFAULT 0.0,
    execution_time_ms INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- HNSW Vector Index for fast Cosine Distance similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Index for Document Summary Vector Search
CREATE INDEX IF NOT EXISTS idx_document_facts_summary_embedding 
ON document_facts USING hnsw (summary_embedding vector_cosine_ops);

-- B-Tree Indexes for rapid exact-match filtering
CREATE INDEX IF NOT EXISTS idx_facts_vendor_client 
ON document_facts (vendor_name, client_name);

-- GIN Index for rapid JSONB querying on document facts
CREATE INDEX IF NOT EXISTS idx_document_facts_facts 
ON document_facts USING gin (facts);

-- Lookup indexes for thread_id and status filters
CREATE INDEX IF NOT EXISTS idx_conflicts_thread_status 
ON conflicts (thread_id, status);

CREATE INDEX IF NOT EXISTS idx_rule_violations_thread_status 
ON rule_violations (thread_id, status);

CREATE INDEX IF NOT EXISTS idx_documents_file_hash 
ON documents (file_hash);


-- Attach UPDATED_AT TRIGGERS
CREATE TRIGGER set_updated_at_documents BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_document_chunks BEFORE UPDATE ON document_chunks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_document_facts BEFORE UPDATE ON document_facts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_rules BEFORE UPDATE ON rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_rule_violations BEFORE UPDATE ON rule_violations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_conflicts BEFORE UPDATE ON conflicts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_deliverables BEFORE UPDATE ON deliverables FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER set_updated_at_execution_logs BEFORE UPDATE ON execution_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();