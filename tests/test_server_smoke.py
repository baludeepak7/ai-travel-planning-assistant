import os
import socket
import subprocess
import sys
import time

import httpx

from src.config import ROOT


def test_streamlit_http_server_starts():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT / "app.py"),
            "--server.headless=true",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
            "--browser.gatherUsageStats=false",
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/_stcore/health", timeout=1)
                if response.status_code == 200:
                    assert response.text == "ok"
                    return
            except httpx.HTTPError:
                pass
            assert process.poll() is None, "Streamlit exited before becoming healthy"
            time.sleep(0.2)
        raise AssertionError("Streamlit did not become healthy within 25 seconds")
    finally:
        process.terminate()
        process.wait(timeout=10)
