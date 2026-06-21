# Product Requirements Document (PRD)

## 1. Executive Summary
The system is a specialized, local dashboard utility designed to automate the downloading and solving of CTFd (Capture The Flag) challenges using LLM agents (Claude Code or Codex). It operates by establishing isolated Docker containers for each challenge workspace, populating them with CTFd metadata, attachments, and toolsets, and streaming the agent's stdout back to a Streamlit user interface in real time. The core value proposition is the orchestration of secure, sandboxed, per-challenge environments for autonomous AI execution.

## 2. System Architecture

### Component Interaction & Data Flow
1. **Frontend (Streamlit)**: 
   - Renders the interactive challenge matrix, status chips, and agent telemetry.
   - Dispatches background thread operations via `concurrent.futures.ThreadPoolExecutor`.
2. **API Client (`ctfd.py`)**: 
   - Interfaces directly with external CTFd infrastructure.
   - Fetches paginated challenges, retrieves individual challenge metadata, and downloads binary attachments.
   - Employs an exponential backoff strategy (`fetch_bytes`) for transient network stability.
3. **Workspace Manager (`workspace.py`)**: 
   - Acts as the local state engine, persisting challenge metadata and run execution state to JSON on disk (`metadata.json`, `state.json`).
   - Generates highly contextual `PROMPT.md` files dynamically compiled from tags, descriptions, hints, and local file paths.
   - Reconciles state discrepancies by querying local Docker daemon metrics.
4. **Agent Orchestration (`agents.py` & Stream Parsers)**: 
   - Constructs and executes `docker run` commands targeting `ctf-ai-solver:latest`.
   - Mounts the specific challenge's local directory into the sandboxed container at `/workspace`.
   - Pipes the raw agent output to disk while secondary parsers (`claude_stream.py`, `codex_stream.py`) extract tool actions and text streams for UI rendering.

## 3. Feature Matrix
The following core features have been explicitly implemented and validated:
- **CTFd Integration**: Synchronize challenge lists and download challenge attachments automatically using session cookies or tokens.
- **Agent Tooling Sandbox**: Custom Dockerfile (`Dockerfile.ctf-tools`) equipped with reverse-engineering suites (pwntools, gdb, radare2, binutils, etc.).
- **Dual-Agent Support**: Native integration for both Anthropic (Claude) and OpenAI (Codex) models.
- **Dynamic Prompt Engineering**: Auto-generation of initial execution prompts (`/goal Solve...`) and contextual follow-up prompts from the UI.
- **Live Telemetry & Streaming**: Background monitoring of Docker containers, streaming raw execution logs, and extracting agent JSON events to the UI.
- **Automated Flag Detection**: Regex-based parsing (`extract_flag_candidates`) to identify potential candidate flags directly from agent stdout.

## 4. Security & Performance

### Security
- **Sandbox Isolation**: All third-party artifacts and untrusted model-generated code execute strictly within per-challenge Docker containers without root filesystem access to the host.
- **Credential Segregation**: Secrets are aggressively excluded from tracking (`.gitignore`) and are loaded purely through local environment variables (via `config.py` loading mechanism) or `os.environ`.
- **API Authentication**: Employs standard HTTP header injection (`Authorization: Token ...` and `Cookie: ...`) for secure CTFd connectivity.

### Performance
- **Connection Resiliency**: HTTP requests include robust exponential backoff up to 3 attempts for standard gateway errors (502, 503, 504) and rate limits (429).
- **Concurrency**: Heavy UI-blocking actions (image builds, CTFd downloads, agent orchestration) are decoupled using an unbound but limited `ThreadPoolExecutor` (max workers: 10), preventing application starvation.
- **Lazy State Hydration**: System logs and states are parsed minimally using disk-seek tailing functions (`tail_text`), ensuring stable memory footprints even with massive LLM context logs.

## 5. Non-Functional Requirements (NFRs)
- **Local Error Handling**: System suppresses silent failures and implements structural `HarnessError` exceptions for all I/O or parsing anomalies.
- **Data Persistence**: Uses an atomic write paradigm (`write_json` utilizing `.tmp` file swapping) to completely mitigate partial write corruption.
- **Logging Protocols**: The system leverages `logging` modules internally for Docker daemon timeouts, but heavily relies on appending raw `.log` artifacts into challenge directories to maintain an immutable audit trail of agent decisions.
- **Test Coverage**: Protected by a 24-test `pytest` suite ensuring URL normalization, workspace lifecycle hooks, log tailing offsets, and JSON validation algorithms remain stable.
