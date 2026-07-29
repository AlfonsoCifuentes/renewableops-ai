"""Scan version-controlled text for high-confidence credential signatures."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts/verification/secret-scan.json"
MAX_FILE_BYTES = 1_000_000
PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,255}\b"),
    "github_fine_grained_token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{80,255}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,255}\b"),
    "stripe_live_key": re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,255}\b"),
    "google_api_key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
}


def tracked_files() -> list[Path]:
    """Return paths controlled by Git, including staged additions."""

    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line]


def main() -> int:
    findings: list[dict[str, object]] = []
    scanned = 0
    for path in tracked_files():
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned += 1
        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(
                        {
                            "rule": rule,
                            "path": path.relative_to(ROOT).as_posix(),
                            "line": line_number,
                        }
                    )
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "passed" if not findings else "failed",
        "scope": "tracked and unignored text files up to 1 MB",
        "files_scanned": scanned,
        "rules": sorted(PATTERNS),
        "findings": findings,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
