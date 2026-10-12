#!/usr/bin/env python3
"""Start the real local CRM API and Next.js UI. Run from an ordinary terminal."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def local_environment() -> dict[str, str]:
    """Load simple KEY=value settings; shell-exported values take precedence."""
    env = os.environ.copy()
    source = ROOT / ".env"
    if source.exists():
        for line in source.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            env.setdefault(key.strip(), value)
    return env


def supported(python: str) -> bool:
    """True when the interpreter is Python 3.11 or 3.12."""
    try:
        result = subprocess.run(
            [python, "-c", "import sys; print(sys.version_info[:2] in ((3, 11), (3, 12)))"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.stdout.strip() == "True"


def prepare_backend() -> str | None:
    """Return the backend venv interpreter, creating it on the first run."""
    venv = ROOT / "backend" / ".venv"
    local_python = venv / "bin" / "python"
    if os.name == "nt":
        local_python = venv / "Scripts" / "python.exe"
    if local_python.exists():
        return str(local_python)
    requirements = str(ROOT / "backend" / "requirements-local.txt")
    print("First run: creating backend/.venv and installing Python packages...", flush=True)
    candidates = [sys.executable, "python3.12", "python3.11"]
    base = next(
        (c for c in candidates if (shutil.which(c) or Path(c).exists()) and supported(c)), None
    )
    uv = shutil.which("uv")
    if base is not None:
        steps = [
            [base, "-m", "venv", str(venv)],
            [str(local_python), "-m", "pip", "install", "-q", "-r", requirements],
        ]
    elif uv is not None:
        steps = [
            [uv, "venv", "--python", "3.11", str(venv)],
            [uv, "pip", "install", "--python", str(local_python), "-r", requirements],
        ]
    else:
        print(
            "Python 3.11 or 3.12 is required (or install uv: https://docs.astral.sh/uv/).",
            file=sys.stderr,
        )
        return None
    for step in steps:
        if subprocess.run(step).returncode != 0:
            shutil.rmtree(venv, ignore_errors=True)
            print("Backend setup failed. Fix the error above and run again.", file=sys.stderr)
            return None
    return str(local_python)


def main() -> int:
    env = local_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=int(env.get("API_PORT", "8010")))
    parser.add_argument("--port", type=int, default=int(env.get("FRONTEND_PORT", "3007")))
    args = parser.parse_args()
    python = env.get("CRM_PYTHON") or prepare_backend()
    npm = shutil.which("npm")
    if python is None:
        return 1
    if npm is None:
        print("Node.js 22+ with npm is required. See docs/native-startup.txt.", file=sys.stderr)
        return 1
    try:
        subprocess.run(
            [python, "-c", "import fastapi, sqlalchemy, uvicorn, pydantic_settings"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(
            "Python dependencies are missing. Delete backend/.venv and run again, or see docs/native-startup.txt.",
            file=sys.stderr,
        )
        return 1
    if not (ROOT / "frontend" / "node_modules" / "next").exists():
        print("First run: installing frontend packages (npm ci)...", flush=True)
        if subprocess.run([npm, "ci"], cwd=ROOT / "frontend").returncode != 0:
            print("npm ci failed. Fix the error above and run again.", file=sys.stderr)
            return 1
    env.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'backend' / 'erp.db'}")
    env.setdefault("ENVIRONMENT", "development")
    env["BACKEND_URL"] = f"http://127.0.0.1:{args.api_port}"
    origins = json.loads(env.get("CORS_ORIGINS", "[]"))
    origins.extend([f"http://localhost:{args.port}", f"http://127.0.0.1:{args.port}"])
    env["CORS_ORIGINS"] = json.dumps(list(dict.fromkeys(origins)))
    children: list[subprocess.Popen] = []

    def stop(signum: int = 0, frame: object = None) -> None:
        for child in children:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        children.append(
            subprocess.Popen(
                [
                    python,
                    "-m",
                    "uvicorn",
                    "app.main:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                    "--no-access-log",
                ],
                cwd=ROOT / "backend",
                env=env,
            )
        )
        children.append(
            subprocess.Popen(
                [npm, "run", "dev", "--", "--hostname", "127.0.0.1", "--port", str(args.port)],
                cwd=ROOT / "frontend",
                env=env,
            )
        )
        print(
            f"Starting Relay CRM at http://127.0.0.1:{args.port}; API at http://127.0.0.1:{args.api_port}. Press Ctrl+C to stop.",
            flush=True,
        )
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        return next(
            (child.returncode for child in children if child.returncode not in (None, 0, -15, -2)),
            0,
        )
    finally:
        stop()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
