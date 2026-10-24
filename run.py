"""All-in-One Launcher for DocSense (FastAPI + Streamlit Review Dashboard).

Usage:
    python run.py
    or double-click run.bat
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

# Detect Python interpreter (prefer project .venv if available)
VENV_PYTHON = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

API_PORT = 8000
UI_PORT = 8501
API_HEALTH_URL = f"http://localhost:{API_PORT}/health"


def wait_for_api(timeout_sec: float = 20.0) -> bool:
    """Poll the API health check endpoint until it responds."""
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        try:
            with urllib.request.urlopen(API_HEALTH_URL, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    print("=" * 60)
    print("       🚀 Launching DocSense (API + Streamlit UI)       ")
    print("=" * 60)

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    env["API_URL"] = f"http://localhost:{API_PORT}"

    # 1. Start FastAPI in background
    print(f"\n[1/2] Starting FastAPI backend on http://localhost:{API_PORT} ...")
    api_cmd = [
        PYTHON_EXE,
        "-m",
        "uvicorn",
        "docint.api.main:app",
        "--port",
        str(API_PORT),
        "--app-dir",
        str(SRC_DIR),
    ]
    api_proc = subprocess.Popen(api_cmd, env=env)

    try:
        # Wait for API to come online
        if not wait_for_api(timeout_sec=25.0):
            print("❌ Error: FastAPI failed to start in time.")
            api_proc.terminate()
            sys.exit(1)

        print(f"      ✅ FastAPI is online at http://localhost:{API_PORT}")
        print(f"      📖 Swagger Docs:   http://localhost:{API_PORT}/docs")

        # 2. Start Streamlit UI
        print(f"\n[2/2] Starting Streamlit dashboard on http://localhost:{UI_PORT} ...")
        print("      🌐 Opening browser automatically...")
        ui_cmd = [
            PYTHON_EXE,
            "-m",
            "streamlit",
            "run",
            str(SRC_DIR / "docint" / "ui" / "app.py"),
            "--server.port",
            str(UI_PORT),
        ]
        ui_proc = subprocess.Popen(ui_cmd, env=env)

        # Keep running until user stops
        print("\n" + "=" * 60)
        print(" DocSense is running! Press Ctrl+C in this window to stop. ")
        print("=" * 60 + "\n")

        ui_proc.wait()

    except KeyboardInterrupt:
        print("\n🛑 Stopping DocSense services...")
    finally:
        # Gracefully shut down both processes
        try:
            api_proc.terminate()
            api_proc.wait(timeout=3)
        except Exception:
            pass

        try:
            ui_proc.terminate()
            ui_proc.wait(timeout=3)
        except Exception:
            pass

        print("✅ DocSense stopped cleanly.")


if __name__ == "__main__":
    main()
