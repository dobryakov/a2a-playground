"""MCP stdio server: envelope tools for A2A-over-git."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer

from . import cursor as cursor_mod
from .config import Config, load_config
from . import gitops
from . import messages as msg_mod

mcp = MCPServer("a2a-over-git")

_cfg: Config | None = None


def get_cfg() -> Config:
    global _cfg
    if _cfg is None:
        _cfg = load_config()
    return _cfg


def set_cfg(cfg: Config) -> None:
    global _cfg
    _cfg = cfg


@mcp.tool()
def post_message(
    to: list[str],
    type: str,
    body: str,
    in_reply_to: str | None = None,
    refs_files: list[str] | None = None,
    refs_locator: str | None = None,
    push: bool = True,
) -> dict[str, Any]:
    """Post an A2A-over-git message, commit it (with optional artifact paths), push.

    Identity (`from`) is set by the server — do not pass it.
    Closing types must match the parent: answer→question, accept/reject→request|propose.
    propose must target *-human endpoints.
    """
    cfg = get_cfg()
    msg_mod.validate_recipients(cfg, to)
    msg_mod.validate_propose_addressee(type, to)

    root: str
    if in_reply_to:
        parent = msg_mod.find_msg(cfg, in_reply_to)
        msg_mod.validate_response_type(parent["type"], type)
        root = parent["root"]
    else:
        root = ""  # filled after id mint

    msg_id = msg_mod.random_id()
    ts = msg_mod.now_utc_iso()
    if not root:
        root = msg_id

    refs: dict[str, Any] = {}
    if refs_files:
        refs["files"] = refs_files
    if refs_locator:
        refs["locator"] = refs_locator

    msg: dict[str, Any] = {
        "id": msg_id,
        "ts": ts,
        "from": cfg.identity,
        "to": to,
        "type": type,
        "in_reply_to": in_reply_to,
        "root": root,
        "refs": refs,
        "body": body,
    }
    msg_mod.validate_schema(msg)

    path = msg_mod.write_msg(cfg, msg)
    to_add: list[str] = [str(path.relative_to(cfg.repo_root))]
    if refs_files:
        to_add.extend(refs_files)
    gitops.add_paths(cfg, to_add)
    gitops.commit_with_trailers(
        cfg,
        subject=msg_mod.commit_summary(msg),
        agent=cfg.identity,
        msg_id=msg_id,
        for_endpoints=to,
    )
    push_result: dict[str, Any] | None = None
    if push:
        push_result = gitops.push_with_retry(cfg)

    return {"id": msg_id, "path": str(path.relative_to(cfg.repo_root)), "push": push_result}


@mcp.tool()
def read_inbox() -> dict[str, Any]:
    """Pull and return unprocessed messages addressed to this agent (not from self)."""
    cfg = get_cfg()
    try:
        gitops.pull_rebase(cfg)
    except gitops.PushConflictError as exc:
        return {"error": "conflict", "detail": str(exc), "messages": []}

    processed = cursor_mod.load_cursor(cfg)
    inbox: list[dict[str, Any]] = []
    for path in msg_mod.list_msg_paths(cfg):
        msg = msg_mod.read_json(path)
        if (
            cfg.identity in msg.get("to", [])
            and msg.get("from") != cfg.identity
            and msg["id"] not in processed
        ):
            inbox.append(msg)
    return {"messages": inbox, "me": cfg.identity}


@mcp.tool()
def get_thread(root_id: str) -> dict[str, Any]:
    """Return all messages in a thread and folded obligation state."""
    cfg = get_cfg()
    msgs = [m for m in msg_mod.all_msgs(cfg) if m.get("root") == root_id]
    ordered = msg_mod.sort_by_causality(msgs)
    return {
        "root": root_id,
        "messages": ordered,
        "state": msg_mod.fold_obligations(ordered),
    }


@mcp.tool()
def pending() -> dict[str, Any]:
    """Open obligations addressed to this identity."""
    cfg = get_cfg()
    obs = [
        ob
        for ob in msg_mod.fold_obligations(msg_mod.all_msgs(cfg))
        if ob["open"] and cfg.identity in ob["to"]
    ]
    return {"pending": obs, "me": cfg.identity}


@mcp.tool()
def mark_processed(message_id: str) -> dict[str, Any]:
    """Mark a message id as processed in the local cursor (.git/agents/)."""
    cfg = get_cfg()
    cursor_mod.mark_processed(cfg, message_id)
    return {"ok": True, "id": message_id}


@mcp.tool()
def whoami() -> dict[str, Any]:
    """Return this server's identity and human owner endpoint."""
    cfg = get_cfg()
    return {
        "me": cfg.identity,
        "human_owner": cfg.human_owner,
        "max_depth": cfg.max_depth,
        "repo_root": str(cfg.repo_root),
    }


def main() -> None:
    # Fail fast if identity missing
    get_cfg()
    mcp.run()


if __name__ == "__main__":
    main()
