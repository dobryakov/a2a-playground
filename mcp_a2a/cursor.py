"""Local cursor: set of processed message ids (lives under .git/agents/)."""

from __future__ import annotations

import json
from pathlib import Path

from .config import Config


def load_cursor(cfg: Config) -> set[str]:
    path = cfg.cursor_path
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("processed_ids", []))


def save_cursor(cfg: Config, processed_ids: set[str]) -> None:
    cfg.agents_local_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.cursor_path
    payload = {"processed_ids": sorted(processed_ids)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mark_processed(cfg: Config, message_id: str) -> None:
    ids = load_cursor(cfg)
    ids.add(message_id)
    save_cursor(cfg, ids)


def compact_cursor(cfg: Config, inbox_ids: set[str]) -> None:
    """Drop ids that are no longer in the inbox (archived)."""
    ids = load_cursor(cfg)
    save_cursor(cfg, ids & inbox_ids)
