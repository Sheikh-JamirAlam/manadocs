# DocTask

## Schema Design

Table `documents` [File Tracker]

- `id` (UUID, Primary Key)
- `filename` (VARCHAR)
- `filepath` (VARCHAR)
- `file_hash` (VARCHAR) — SHA-256 hash to detect duplicate files
- `file_size_bytes` (BIGINT)
- `document_type` (VARCHAR) — 'contract', 'amendment', 'invoice', or 'unknown'
- `vendor_name` (VARCHAR)
- `status` (VARCHAR) — 'pending', 'processing', 'processed', 'flagged', 'failed'
- `error_message` (TEXT)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `document_chunks` [Vector Store for RAG]

- `id` (UUID, Primary Key)
- `document_id` (UUID, Foreign Key -> documents.id)
- `chunk_index` (INT)
- `content` (TEXT) — The raw text of the chunk
- `embedding` (VECTOR(1536)) — pgvector embedding column
- `metadata` (JSONB) — Page numbers, section headers, etc.
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `extracted_facts` [Structured Output]

- `id` (UUID, Primary Key)
- `document_id` (UUID, Foreign Key -> documents.id)
- `facts` (JSONB) — Single JSON payload of extracted key-value pairs with nested citations (page numbers, quotes)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `rules` [Business Policies]

- `id` (UUID, Primary Key)
- `rule_code` (VARCHAR) — e.g., 'RULE_MAX_INVOICE_AMOUNT'
- `name` (VARCHAR)
- `description` (TEXT)
- `condition_params` (JSONB) — Threshold parameters (e.g., `{"max_amount": 10000}`)
- `is_active` (BOOLEAN)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `rule_violations ` [Single-Document Policy Breaks]

- `id` (UUID, Primary Key)
- `thread_id` (VARCHAR) — Maps directly to the LangGraph execution thread
- `document_id` (UUID, Foreign Key -> documents.id)
- `rule_id` (UUID, Foreign Key -> rules.id)
- `severity` (VARCHAR) — 'high', 'medium', 'low'
- `description` (TEXT) — Human-readable summary of the rule violation
- `citation` (JSONB) — Page number and quote breaking the rule
- `status` (VARCHAR) — 'pending', 'resolved'
- `resolution` (VARCHAR) — 'enforce_rule', 'override_rule'
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `contradictions` [Two-Document Conflicts]

- `id` (UUID, Primary Key)
- `thread_id` (VARCHAR) — Maps directly to the LangGraph execution thread
- `doc_a_id` (UUID, Foreign Key -> documents.id)
- `doc_b_id` (UUID, Foreign Key -> documents.id)
- `field_name` (VARCHAR) — e.g., 'hourly_rate'
- `doc_a_value` (JSONB) — Extracted value and citation for Document A
- `doc_b_value` (JSONB) — Extracted value and citation for Document B
- `status` (VARCHAR) — 'pending', 'resolved'
- `selected_doc_id` (UUID, Foreign Key -> documents.id) — Stores the chosen document UUID upon review
- `resolution` (VARCHAR) — 'use_doc_a', 'use_doc_b'
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `deliverables` [Master Report]

- `id` (UUID, Primary Key)
- `thread_id` (VARCHAR)
- `title` (VARCHAR)
- `content` (TEXT) — Current draft of the deliverable
- `version` (INT) — Incrementing version number on updates
- `status` (VARCHAR) — 'draft', 'review_required', 'finalized'
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

Table `execution_logs` [Telemetry & Cost Tracking]

- `id` (UUID, Primary Key)
- `thread_id` (VARCHAR)
- `node_name` (VARCHAR) — e.g., 'extract_facts', 'audit_rules'
- `tokens_prompt` (INT)
- `tokens_completion` (INT)
- `estimated_cost` (NUMERIC)
- `execution_time_ms` (INT)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
