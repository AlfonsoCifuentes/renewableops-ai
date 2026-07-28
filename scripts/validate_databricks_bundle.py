"""Validate the bundle schema against a loopback-only Databricks API stub.

This checks interpolation and the current CLI resource schema without claiming
that remote workspace permissions or capabilities were exercised.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path.startswith("/api/2.0/preview/scim/v2/Me"):
            payload = {
                "id": "offline-validator",
                "userName": "offline-validator@example.invalid",
                "displayName": "Offline Validator",
                "active": True,
                "groups": [],
            }
            self._json(200, payload)
        elif self.path.startswith("/api/2.0/workspace/get-status"):
            self._json(
                200,
                {
                    "path": "/Workspace/Users/offline-validator/.bundle",
                    "object_type": "DIRECTORY",
                    "object_id": 1,
                },
            )
        elif self.path.startswith("/.well-known/databricks-config"):
            self._json(
                200,
                {
                    "workspace_id": "offline",
                    "cloud": "aws",
                    "oidc_endpoint": f"http://{self.headers['Host']}/oidc",
                },
            )
        else:
            self._json(404, {"error_code": "NOT_FOUND", "message": self.path})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path.startswith("/api/2.0/workspace/mkdirs"):
            self._json(200, {})
        else:
            self._json(404, {"error_code": "NOT_FOUND", "message": self.path})

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _json(self, status: int, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cli", type=Path)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    environment = os.environ.copy()
    environment.update(
        {
            "DATABRICKS_HOST": f"http://{host}:{port}",
            "DATABRICKS_TOKEN": "offline-structural-validation",
        }
    )
    try:
        completed = subprocess.run(
            [
                str(args.cli),
                "bundle",
                "validate",
                "-t",
                "dev",
                "--strict",
                "--var=warehouse_id=offline-warehouse",
            ],
            cwd=Path(__file__).resolve().parents[1] / "databricks",
            env=environment,
            check=False,
        )
        return completed.returncode
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
