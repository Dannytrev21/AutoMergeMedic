#!/usr/bin/env python3
"""Generate all AutoMergeMedic diagrams (PNG + SVG)."""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

SCRIPTS = [
    "circuit_breaker_diagram.py",
    "state_machine_diagram.py",
    "architecture_diagram.py",
    "reconciler_flow_diagram.py",
    "sequence_diagrams.py",
]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    venv_python = os.path.join(SCRIPT_DIR, "..", ".venv", "bin", "python3")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable

    failed = []
    for script in SCRIPTS:
        script_path = os.path.join(SCRIPT_DIR, script)
        print(f"  Generating: {script} ...", end=" ", flush=True)
        result = subprocess.run(
            [python_exe, script_path],
            capture_output=True,
            text=True,
            cwd=SCRIPT_DIR,
        )
        if result.returncode != 0:
            print("FAILED")
            print(f"    stderr: {result.stderr.strip()}")
            failed.append(script)
        else:
            print("OK")

    print()
    if failed:
        print(f"{len(failed)} script(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        files = [f for f in os.listdir(OUTPUT_DIR) if not f.startswith(".")]
        print(f"All diagrams generated — {len(files)} files in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
