from __future__ import annotations

import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    return subprocess.run(["streamlit", "run", "streamlit_app.py", *args], check=False).returncode
