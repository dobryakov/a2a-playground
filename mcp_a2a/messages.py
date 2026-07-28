"""Message schema, validation, I/O, obligation fold."""

from __future__ import annotations

import json
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Config

OPENING_TYPES = frozenset({"question", "request", "propose"})
CLOSING = {
    "answer": frozenset({"question"}),
    "accept": frozenset({"request", "propose"}),
    "reject": frozenset({"request", "propose"}),
}
ALL_TYPES = frozenset(
    {"inform", "question", "request", "propose", "answer", "accept", "reject"}
)


class ProtocolError(ValueError):
    pass


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def random_id(n: int = 8) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def fs_safe_ts(ts: str) -> str:
    return ts.replace(":", "-")


def msg_filename(ts: str, frm: str, msg_id: str) -> str:
    return f"{fs_safe_ts(ts)}__{frm}__{msg_id}.json"


def validate_recipients(cfg: Config, to: list[str]) -> None:
    if not to:
        raise ProtocolError("`to` must be a non-empty list of endpoints")
    for ep in to:
        if cfg.endpoints and ep not in cfg.endpoints:
            raise ProtocolError(f"unknown recipient endpoint: {ep!r}")
        if not (ep.endswith("-agent") or ep.endswith("-human")):
            raise ProtocolError(f"endpoint must end with -agent or -human: {ep!r}")


def validate_response_type(parent_type: str, reply_type: str) -> None:
    if reply_type in CLOSING:
        allowed_parents = CLOSING[reply_type]
        if parent_type not in allowed_parents:
            raise ProtocolError(
                f"{reply_type!r} can only reply to {sorted(allowed_parents)}, "
                f"not {parent_type!r}"
            )
    # opening / inform as replies are allowed (continue thread)


def validate_propose_addressee(msg_type: str, to: list[str]) -> None:
    if msg_type == "propose":
        if not all(ep.endswith("-human") for ep in to):
            raise ProtocolError("`propose` must be addressed to *-human endpoint(s)")


def validate_schema(msg: dict[str, Any]) -> None:
    required = ("id", "ts", "from", "to", "type", "root", "body")
    for key in required:
        if key not in msg:
            raise ProtocolError(f"missing field: {key}")
    if msg["type"] not in ALL_TYPES:
        raise ProtocolError(f"unknown type: {msg['type']!r}")
    if not isinstance(msg["to"], list) or not msg["to"]:
        raise ProtocolError("`to` must be a non-empty list")
    if not isinstance(msg["body"], str) or not msg["body"].strip():
        raise ProtocolError("`body` must be a non-empty string")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_msg(cfg: Config, msg: dict[str, Any]) -> Path:
    cfg.msgs_dir.mkdir(parents=True, exist_ok=True)
    path = cfg.msgs_dir / msg_filename(msg["ts"], msg["from"], msg["id"])
    path.write_text(
        json.dumps(msg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return path


def list_msg_paths(cfg: Config) -> list[Path]:
    if not cfg.msgs_dir.is_dir():
        return []
    paths = sorted(cfg.msgs_dir.glob("*.json"))
    return paths


def all_msgs(cfg: Config) -> list[dict[str, Any]]:
    return [read_json(p) for p in list_msg_paths(cfg)]


def find_msg(cfg: Config, msg_id: str) -> dict[str, Any]:
    for msg in all_msgs(cfg):
        if msg["id"] == msg_id:
            return msg
    raise ProtocolError(f"message not found: {msg_id}")


def reply_depth(cfg: Config, msg: dict[str, Any]) -> int:
    depth = 0
    current = msg
    seen: set[str] = set()
    while current.get("in_reply_to"):
        mid = current["id"]
        if mid in seen:
            break
        seen.add(mid)
        depth += 1
        current = find_msg(cfg, current["in_reply_to"])
    return depth


def sort_by_causality(msgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {m["id"]: m for m in msgs}
    depth: dict[str, int] = {}

    def d(mid: str) -> int:
        if mid in depth:
            return depth[mid]
        m = by_id[mid]
        parent = m.get("in_reply_to")
        depth[mid] = 0 if not parent or parent not in by_id else 1 + d(parent)
        return depth[mid]

    return sorted(msgs, key=lambda m: (d(m["id"]), m.get("ts", ""), m["id"]))


def fold_obligations(msgs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive open/closed obligations from an immutable message log."""
    by_parent: dict[str, list[dict[str, Any]]] = {}
    for m in msgs:
        parent = m.get("in_reply_to")
        if parent:
            by_parent.setdefault(parent, []).append(m)

    obligations: list[dict[str, Any]] = []
    for m in msgs:
        if m["type"] not in OPENING_TYPES:
            continue
        children = by_parent.get(m["id"], [])
        closed_by = None
        for child in children:
            if child["type"] in CLOSING and m["type"] in CLOSING[child["type"]]:
                closed_by = child["id"]
                break
        obligations.append(
            {
                "id": m["id"],
                "type": m["type"],
                "from": m["from"],
                "to": m["to"],
                "root": m["root"],
                "body": m["body"],
                "open": closed_by is None,
                "closed_by": closed_by,
            }
        )
    return obligations


def commit_summary(msg: dict[str, Any]) -> str:
    tip = msg["body"].strip().splitlines()[0][:72]
    return f"a2a({msg['type']}): {tip}"
