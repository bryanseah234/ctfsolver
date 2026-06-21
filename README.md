# Developer README

![Dashboard](./image.png)

## 1. Project Overview
This repository contains a local Streamlit dashboard and testing harness designed to bridge the gap between Capture The Flag (CTF) platforms and autonomous Large Language Model agents. It automates the extraction of challenges from CTFd, mounts them into isolated, tool-rich Docker containers, and manages the lifecycle of AI agents (Claude Code or Codex) attempting to solve them. Telemetry, active state tracking, and parsed execution logs are rendered in the frontend dashboard.

## 2. Prerequisites
Ensure the following tools are installed on the host system:
- **Python**: `>=3.11`
- **Docker Engine**: Required to build the custom `Dockerfile.ctf-tools` image and spawn per-challenge containers.
- **uv**: Python package and project manager (recommended over standard `pip` for rapid virtual environment caching).

## 3. Environment Configuration
The application relies strictly on environment variables for API authentication and tooling preferences. You must copy the provided `.env.example` file to `.env` and populate the necessary rows.

| Variable | Description | Required For |
| :--- | :--- | :--- |
| `CTFD_TOKEN` | A long-lived access token generated from your CTFd instance. | Downloading CTFd challenges |
| `CTFD_COOKIE` | Fallback session cookie (if token access is unavailable). | Downloading CTFd challenges |
| `ANTHROPIC_API_KEY` | Your Anthropic platform API key. | Executing Claude |
| `ANTHROPIC_AUTH_TOKEN`| OAuth token for Claude Code CLI. | Executing Claude (OAuth mode) |
| `CLAUDE_CODE_OAUTH_TOKEN`| Alias for Anthropic Auth Token. | Executing Claude (OAuth mode) |
| `CTF_HARNESS_CLAUDE_PARTIAL_MESSAGES` | Toggles live message streaming inside the UI (defaults to 1). | Claude UI telemetry |
| `OPENAI_API_KEY` | Your OpenAI platform API key. | Executing Codex |
| `CODEX_ACCESS_TOKEN` | Direct access token for the Codex engine. | Executing Codex |
| `CTF_HARNESS_CODEX_MODEL`| Model override (defaults to `gpt-5.4`). | Executing Codex |

> **Note**: Do not commit the `.env` file to version control.

## 4. Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Synchronize dependencies:**
   The project uses `uv` for lightning-fast dependency resolution. Run the following command to sync the virtual environment with `pyproject.toml` and `uv.lock`:
   ```bash
   uv sync
   ```

3. **Build the Docker Image:**
   Before running any agents, build the necessary sandboxing image containing the required CTF binaries.
   ```bash
   docker build -t ctf-ai-solver:latest -f Dockerfile.ctf-tools .
   ```

4. **Environment Setup:**
   ```bash
   cp .env.example .env
   # Open .env and add your respective tokens.
   ```

## 5. Usage & Testing

### Running the Dashboard
To boot the Streamlit application, execute the following from the root directory:
```bash
uv run streamlit run streamlit_app.py
```
*Navigate to the local URL (typically `http://localhost:8501`) provided in your terminal.*

### Running the Test Suite
The repository maintains a robust local test suite encompassing utilities, API retry mechanics, and workspace state generation. To run all tests and verify the system health:
```bash
uv run pytest -v
```
If you encounter `ModuleNotFoundError` during tests, ensure `pyproject.toml` has `pythonpath = ["src"]` defined in its `pytest.ini_options` block (which is enabled by default).
