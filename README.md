# DocTask

DocTask is an agentic document-review system for vendor contracts, amendments,
invoices, and other documents that describe the same business transaction.

It watches a folder for new documents, extracts grounded facts with citations,
matches related documents, detects conflicts, checks configurable business
rules, and produces a consolidated deliverable. Conflicts and rule findings are
paused for human review before the workflow continues. Workflow state is
checkpointed in PostgreSQL, and progress is available through Server-Sent
Events so a client can display each stage as it runs.

## Start with Docker

Docker is the recommended way to run the complete system. It starts the API and
the PostgreSQL/pgvector database together.

### Prerequisites

- Docker Desktop on Windows/macOS, or Docker Engine and Compose on Linux
- A Gemini API key
- A local folder containing synthetic or public documents you are permitted to process

### Setup

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set `GEMINI_API_KEY`, `PGPASSWORD`, and `HOST_WATCH_FOLDER`.
   `HOST_WATCH_FOLDER` must point to an existing local folder containing
   documents.

3. Start the API and database from the repository root:

   ```bash
   docker compose up --build
   ```

   The API is available at [http://localhost:8000](http://localhost:8000).
   The host watch folder is mounted into the backend as `/data/documents`.

4. To run in the background:

   ```bash
   docker compose up --build -d
   ```

5. To stop the system:

   ```bash
   docker compose down
   ```

   Add `-v` only when you intentionally want to remove the PostgreSQL data
   volume and start with a fresh database.

## Workflow and API

The workflow moves through these stages:

1. Analyze and extract cited facts.
2. Find related documents.
3. Review and resolve conflicts.
4. Check the configured rules.
5. Review and resolve rule findings.
6. Generate or update the deliverable.

Resolution requests return immediately with a queued response. The backend
continues the workflow asynchronously.

Useful endpoints include:

```text
POST /conflicts/resolve
POST /rules/resolve
GET  /workflow/{thread_id}/events
GET  /workflow/{thread_id}/events/stream

POST /mcp  (Streamable HTTP MCP server)
```

The SSE endpoint emits durable workflow events and supports reconnecting with
the `Last-Event-ID` header or the `after` query parameter.

The MCP server exposes machine-callable tools for workflow status, event
history, pending conflicts, conflict resolution, pending rule violations, rule
resolution, and rule creation. MCP clients connect to
`http://localhost:8000/mcp` and can drive the same human-gated workflow as the
REST API. A machine client can approve or reject findings, but it cannot bypass
the workflow's state checks or silently commit a review decision.

## Data and safety

Use synthetic, public, or otherwise authorized documents only. Document text is
treated as untrusted data; instructions found inside a source document are not
workflow commands. Extracted claims and findings retain source citations so the
result can be reviewed against the original documents.
