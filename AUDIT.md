# SYSTEM CODEBASE AUDIT & REMEDIATION REPORT

## ══ 0. FILESYSTEM HEALTH REPORT ══

- **Corrupted files**: None detected.
- **Orphaned files**: 
  - `ctf_harness.py` | Standalone script wrapper for Streamlit. | EXPENDABLE | Keep if used as a convenience script, otherwise remove.
  - `ctf_harness_app/dashboard.py` | Script wrapper module. | EXPENDABLE | Consolidate with `ctf_harness.py` or remove, as `README.md` instructs running `streamlit_app.py` directly.
- **Sync artifacts**: None detected.

---

## ══ 1. MASTER FEATURE MAP (SOURCE OF TRUTH) ══

### Module: `ctf_harness_app.config`
- **Path**: `ctf_harness_app/config.py`
- **Purpose**: Configuration defaults and environment loading.
- **Key Functions**:
  - `load_dotenv()`: Parses `.env` manually and injects into `os.environ` if not already set.

### Module: `ctf_harness_app.util`
- **Path**: `ctf_harness_app/util.py`
- **Purpose**: General utilities, file operations, and string manipulation.
- **Key Functions**:
  - `read_json()`, `write_json()`: Atomic JSON file I/O using `.tmp` file replacements.
  - `tail_text()`: Reads the end of large log files.
  - `extract_flag_candidates()`: Uses regex `\b[A-Za-z0-9_.-]{0,32}\{[^{}\s]{4,200}\}` to find flags in agent outputs.

### Module: `ctf_harness_app.ctfd`
- **Path**: `ctf_harness_app/ctfd.py`
- **Purpose**: API client for CTFd to download challenges and attachments.
- **Key Functions**:
  - `CTFdClient.list_challenges()`, `CTFdClient.get_challenge()`: Fetches challenge metadata with pagination support.
  - `CTFdClient.download_file()`: Downloads attachments.
- **Dependencies**: `urllib` (Standard Library). Reads `CTFD_TOKEN` and `CTFD_COOKIE`.

### Module: `ctf_harness_app.workspace`
- **Path**: `ctf_harness_app/workspace.py`
- **Purpose**: Manages local filesystem state for challenges (`state.json`, `metadata.json`, `PROMPT.md`).
- **Key Functions**:
  - `build_prompt()`, `build_followup_prompt()`: Generates prompt files from CTFd metadata.
  - `download_challenges()`: Orchestrates downloading from CTFd to the local directory.
  - `reconcile_stale_runs()`: Checks `docker ps` to reconcile UI state if an agent container dies silently.
  - `collect_dashboard()`: Aggregates state across all challenges for the Streamlit UI.

### Module: `ctf_harness_app.agents`
- **Path**: `ctf_harness_app/agents.py`
- **Purpose**: Orchestrates Docker containers and agent CLI execution.
- **Key Functions**:
  - `run_streaming_agent()`: Spawns Docker as a subprocess, streams stdout to log files, handles 5-second heartbeats, and detects idle timeouts.
  - `claude_inner_command()`, `codex_inner_command()`: Constructs the shell scripts executed *inside* the Docker container.
  - `docker_command()`: Builds the `docker run` command with mounts, security options, and network settings.
- **Dependencies**: Requires `docker` CLI on host.

### Module: Stream Parsers
- **Paths**: `ctf_harness_app/claude_stream.py`, `ctf_harness_app/codex_stream.py`
- **Purpose**: Parses native JSONL streams from Claude Code and Codex into a standard event format for rendering in the dashboard.

### Module: Main Dashboard
- **Path**: `streamlit_app.py`
- **Purpose**: Main Streamlit user interface.
- **Key Functions**: `render_live_dashboard()`, `render_challenge()`, `render_sidebar()`. Spawns background threads for agent executions and downloads.

---

## ══ 2. RECONCILIATION SUMMARY ══

- **Truth Gap**: ~5%. The documentation accurately describes the `/goal` loop and Docker usage. However, it omits internal mechanisms like stale container reconciliation and local heartbeat tracking.
- **State of System**: The system is a mature, specialized local tool. It handles agent streaming and Docker sandboxing robustly but lacks production-grade reliability features (like network retries or automated tests) appropriate for a local desktop application.
- **Production Readiness Score**: 4/15 checklist items passing. (Expected for a local utility, but missing some robustness).

---

## ══ 3. CRITICAL GAPS (UNIMPLEMENTED FEATURES) ══

| Feature | Source Doc | Severity | Reason it matters |
| :--- | :--- | :--- | :--- |
| None identified | N/A | N/A | All stated features in `README.md` are implemented. |

---

## ══ 4. UNDOCUMENTED LOGIC (GHOST FEATURES) ══

| Module/Function | File Path | What it does | Why it should be documented |
| :--- | :--- | :--- | :--- |
| `reconcile_stale_runs` | `workspace.py` | Polls `docker ps` to mark runs as stopped if the container crashes or is killed externally. | Clarifies that the dashboard auto-recovers from out-of-band Docker interventions. |
| Stream partial parsing | `claude_stream.py` | Extracts tool inputs incrementally from Claude stream blocks. | Helps developers understand how UI renders live tool typing. |

---

## ══ 5. DOCUMENTATION DRIFT ══

| Documented Behavior | Actual Behavior | File Path | Correction Needed |
| :--- | :--- | :--- | :--- |
| `README.md` instructs running `uv run streamlit run streamlit_app.py` | `ctf_harness.py` and `ctf_harness_app/dashboard.py` exist as alternate wrappers. | Multiple | Remove the wrappers or document them. |

---

## ══ 6. DATA INTEGRITY REPORT ══

The application uses JSON files (`state.json`, `.harness-state.json`, `metadata.json`) instead of a traditional DB.
- **Schema Match**: PASS. The shape of state dictionaries in `workspace.py` matches the loaded data.
- **Incomplete Writes**: None detected. Uses atomic `.tmp` replace pattern in `util.py:write_json`.
- **Recommended Action**: Monitor JSON scale; if challenge history grows huge, JSON loading in `collect_dashboard` may bottleneck Streamlit.

---

## ══ 7. CODE QUALITY FINDINGS ══

| Tag | Description | File Path | Function Name | Severity | Fix |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `[RELIABILITY]` | No HTTP retry logic for CTFd API calls. | `ctf_harness_app/ctfd.py` | `fetch_bytes` | P2 | Wrap `urllib.request.urlopen` in a retry loop with exponential backoff. |
| `[RELIABILITY]` | Hardcoded 5s timeout on `docker ps` can silently fail reconciliation if Docker daemon is slow. | `ctf_harness_app/workspace.py` | `active_container_names` | P2 | Log a warning if `docker ps` times out instead of silently failing. |
| `[DEAD]` | `dashboard.py` wrapper exists but is undocumented and duplicates `ctf_harness.py`. | `ctf_harness_app/dashboard.py` | `main` | P3 | Delete or consolidate. |
| `[PERFORMANCE]` | Background tasks use unbound raw threads without a thread pool or queue. | `streamlit_app.py` | `run_background` | P3 | Use `concurrent.futures.ThreadPoolExecutor`. |

---

## ══ 8. STRUCTURAL REORGANIZATION PLAN ══

**8a. Current File Tree**
```text
.
├── ctf_harness_app/
│   ├── __init__.py, agents.py, claude_stream.py, codex_stream.py, config.py, ctfd.py, dashboard.py, util.py, workspace.py
├── .gitignore, Dockerfile.ctf-tools, README.md, ctf_harness.py, pyproject.toml, streamlit_app.py, uv.lock
```

**8b. Target File Tree**
```text
.
├── src/
│   ├── ctf_harness_app/  (Move package here)
├── .gitignore, Dockerfile.ctf-tools, README.md, pyproject.toml, streamlit_app.py, uv.lock
```

**8c. Move Plan**
| Step | Action | Source Path | Destination Path | Protected? | Backup Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Create | N/A | `src/` | No | No |
| 2 | Move | `ctf_harness_app/` | `src/ctf_harness_app/` | No | No |
| 3 | Delete | `ctf_harness.py` | N/A | No | No |

**8e. .gitignore Additions**
- `challenges/` (Reason: Prevents committing downloaded CTF state and agent logs)
- `.env` (Reason: Already likely ignored, but explicit protection required)
- `__pycache__/`

---

## ══ 9. PRODUCTION READINESS CHECKLIST ══

- [PASS] All secrets externalized to environment variables.
- [N/A] All database migrations versioned. (No database used).
- [PASS] All file writes are atomic or guarded against partial-write corruption. (`util.write_json`)
- [FAIL] All external API calls have timeout and retry configurations. (Timeouts exist, retries do not).
- [FAIL] Logging is structured. (Agent logs are plain text, app logs are minimal).
- [FAIL] Graceful shutdown handling present. (Background threads are daemonized, but no signal trapping).
- [FAIL] Test coverage exists. (No tests found).

*Justification*: This is a local desktop utility designed to run locally on a CTF player's machine, so strict production web-server readiness (rate limiting, structured logs) is largely N/A or overkill.

---

## ══ 10. PRIORITIZED REMEDIATION ROADMAP ══

| Priority | Action | Rationale | Files Affected | Estimated Effort |
| :--- | :--- | :--- | :--- | :--- |
| 1 | P1 / Data Loss | Ensure `.gitignore` explicitly ignores `challenges/` and `.env` to prevent credential leakage. | `.gitignore` | S |
| 2 | P2 / Reliability | Add backoff/retry logic to CTFd API client. | `ctf_harness_app/ctfd.py` | S |
| 3 | Structural | Move `ctf_harness_app` to `src/` directory and remove redundant wrappers. | File tree | S |
| 4 | P3 / Code Quality | Replace raw threading with a proper `ThreadPoolExecutor`. | `streamlit_app.py` | S |
