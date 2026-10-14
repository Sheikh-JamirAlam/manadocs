# ManaDocs

ManaDocs is an agentic document-review system for vendor contracts, amendments, invoices, and other documents that describe the same business transaction.

It watches a folder for new documents, extracts grounded facts with citations, matches related documents, detects conflicts, checks configurable business rules, and produces a consolidated deliverable. Conflicts and rule findings are paused for human review before the workflow continues. Workflow state is checkpointed in PostgreSQL, and progress is available through Server-Sent Events so a client can display each stage as it runs.

## System Architecture

ManaDocs uses a React frontend, a FastAPI backend, a LangGraph workflow, and PostgreSQL with pgvector. Documents can enter through the watched folder, the REST API, or the MCP server. All entry points converge on the same queued workflow and human review gates.

![System Architecture Diagram](/assets/system-architecture.png)

### Request and data flow

1. A document is uploaded, submitted through MCP, or detected in the watched folder.
2. The backend queues a workflow and extracts cited, reviewable facts.
3. Related documents are matched and cross-document conflicts are identified.
4. The workflow pauses for conflict review, then checks configurable business rules.
5. Rule findings are reviewed before the final deliverable is generated or updated.
6. Workflow events are persisted and streamed to the frontend over SSE, while PostgreSQL checkpoints allow interrupted workflows to resume.

The same workflow and state checks are used by the UI and MCP clients, so machine-driven actions cannot bypass human-gated review decisions.

## Start with Docker

Docker is the recommended way to run the complete system. `docker compose up` starts the backend, frontend, and PostgreSQL/pgvector database together. The frontend is served at [http://localhost:3000](http://localhost:3000).

### Prerequisites

- Docker Desktop on Windows/macOS, or Docker Engine and Compose on Linux
- A Gemini API key
- A local folder containing synthetic or public documents you are permitted to process

### Setup

1. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set the required API, database, and host watch-folder variables; `HOST_WATCH_FOLDER` must point to an existing local folder containing documents.

3. Start the backend, frontend, and database from the repository root:

   ```bash
   docker compose up --build
   ```

   The frontend is available at [http://localhost:3000](http://localhost:3000), and the API is available at [http://localhost:8000](http://localhost:8000). The host watch folder is mounted into the backend as `/data/documents`.

4. To run in the background:

   ```bash
   docker compose up --build -d
   ```

5. To stop the system:

   ```bash
   docker compose down
   ```

   Add `-v` only when you intentionally want to remove the PostgreSQL data volume and start with a fresh database.

### Environment variables

The `.env` file is loaded by Docker Compose. Start from `.env.example`, replace the placeholder values, and keep the file out of version control.

| Variable                 | Description                                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| `GEMINI_API_KEY`         | API key used by the backend’s Gemini model provider for document analysis and deliverable generation.                          |
| `PGDATABASE`             | PostgreSQL database name used by the application and database container.                                                       |
| `PGUSER`                 | PostgreSQL username used by the application and database container.                                                            |
| `PGPASSWORD`             | PostgreSQL password used by the application and database container. Use a strong local value.                                  |
| `HOST_WATCH_FOLDER`      | Absolute path to the host folder monitored for new documents. Docker mounts this folder into the backend as `/data/documents`. |
| `WATCH_INTERVAL_SECONDS` | Number of seconds between folder-watcher scans.                                                                                |
| `MAX_WORKFLOW_RETRIES`   | Maximum number of retries for a failed watched-document workflow.                                                              |
| `VITE_API_BASE_URL`      | Backend base URL compiled into the frontend. For the Docker setup, use `http://localhost:8000`.                                |

### Local frontend with Docker backend

Run only the backend and PostgreSQL containers:

```bash
docker compose up backend postgres
```

In a second terminal, run the frontend from the `frontend` directory:

```bash
cd frontend
bun dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The frontend defaults to `http://localhost:8000` for the API, and the backend allows the Vite development origins.

## How to Run a Document Review

After starting the system with Docker, documents can be submitted in either of these ways:

1. **Drop files into the file pipe:** Place a PDF, DOCX, or TXT file in the folder configured by `HOST_WATCH_FOLDER`. The backend watches this mounted folder and automatically starts a workflow for each new document.
2. **Upload files in the frontend:** Open [http://localhost:3000](http://localhost:3000), use the document upload control, and submit the file through the web interface.

Both paths use the same backend workflow, review gates, persistence, and deliverable-generation process. Files from `assets` directory can be used. These are synthetic files made for testing the System.

## Workflow and API

The workflow moves through these stages:

1. Analyze and extract cited facts.
2. Find related documents.
3. Review and resolve conflicts.
4. Check the configured rules.
5. Review and resolve rule findings.
6. Generate or update the deliverable.

Resolution requests return immediately with a queued response. The backend continues the workflow asynchronously.

Useful endpoints include:

```text
POST /conflicts/resolve
POST /rules/resolve
GET  /workflow/{thread_id}/events
GET  /workflow/{thread_id}/events/stream

POST /mcp  (Streamable HTTP MCP server)
```

The SSE endpoint emits durable workflow events and supports reconnecting with the `Last-Event-ID` header or the `after` query parameter.

The MCP server exposes machine-callable tools for workflow status, event history, pending conflicts, conflict resolution, pending rule violations, rule resolution, and rule creation. MCP clients connect to `http://localhost:8000/mcp` and can drive the same human-gated workflow as the REST API. A machine client can approve or reject findings, but it cannot bypass the workflow's state checks or silently commit a review decision.

MCP clients can also use `submit_document(filename, content_base64)`. The decoded document is saved into the configured `WATCH_FOLDER` and registered through the same path as a frontend upload, returning the document and workflow thread identifiers.

## Data and safety

Use synthetic, public, or otherwise authorized documents only. Document text is treated as untrusted data; instructions found inside a source document are not workflow commands. Extracted claims and findings retain source citations so the result can be reviewed against the original documents.

## Tests

The backend has integration tests that run without a Gemini API key. They use a real temporary `pgvector/pgvector:pg17` PostgreSQL container and a deterministic local model provider at the model boundary. The suite covers:

- Checkpoint persistence and resuming after a conflict gate.
- Two workflows running concurrently with isolated thread state.
- Prompt-injection text remaining untrusted document data.
- Machine-driven MCP status and conflict-resolution operations.
- Gemini/provider failures resulting in a failed document status.

Start Docker Desktop, then run from the repository root:

```bash
cd backend
uv run pytest -q tests
```

For detailed test output:

```bash
cd backend
uv run pytest -vv tests
```

The tests start and remove their own temporary PostgreSQL container. No live Gemini key or frontend is required.
