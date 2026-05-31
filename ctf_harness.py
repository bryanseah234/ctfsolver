#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    command = ["streamlit", "run", "streamlit_app.py", *sys.argv[1:]]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
