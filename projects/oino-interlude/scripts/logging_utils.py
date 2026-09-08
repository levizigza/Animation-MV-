"""Structured logging helpers for Oino pipeline scripts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunReport:
    """Collect created / reused / skipped / failed lines; write versioned JSON."""

    script: str
    seed: int | None = None
    reset: bool = False
    created: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now)
    finished_at: str | None = None
    ok: bool = True

    def mark(self, status: str, item: str) -> None:
        status = status.lower()
        bucket = {
            "created": self.created,
            "reused": self.reused,
            "skipped": self.skipped,
            "failed": self.failed,
        }.get(status)
        if bucket is None:
            self.notes.append(f"unknown_status:{status}:{item}")
            return
        bucket.append(item)
        prefix = status.upper()
        print(f"[{prefix}] {item}")

    def fail(self, item: str, exc: BaseException | str) -> None:
        self.ok = False
        msg = f"{item}: {exc}"
        self.failed.append(msg)
        print(f"[FAILED] {msg}")

    def note(self, text: str) -> None:
        self.notes.append(text)
        print(f"[NOTE] {text}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "script": self.script,
            "seed": self.seed,
            "reset": self.reset,
            "ok": self.ok,
            "started_at": self.started_at,
            "finished_at": self.finished_at or utc_now(),
            "counts": {
                "created": len(self.created),
                "reused": len(self.reused),
                "skipped": len(self.skipped),
                "failed": len(self.failed),
            },
            "created": self.created,
            "reused": self.reused,
            "skipped": self.skipped,
            "failed": self.failed,
            "notes": self.notes,
        }

    def write(self, reports_dir: Path) -> Path:
        self.finished_at = utc_now()
        reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe = self.script.replace(" ", "_").replace("/", "_")
        path = reports_dir / f"{safe}_{stamp}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        latest = reports_dir / f"{safe}_latest.json"
        latest.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        print(f"[REPORT] {path}")
        return path
