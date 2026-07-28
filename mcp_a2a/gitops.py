"""Git operations for the envelope: pull/rebase, commit with trailers, push retry."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Config


class GitError(RuntimeError):
    pass


class PushConflictError(GitError):
    """Artifact conflict during rebase — escalate to human (invariant 9)."""


def _run(
    cfg: Config,
    args: list[str],
    *,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cfg.repo_root,
        text=True,
        input=input_text,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def pull_rebase(cfg: Config) -> None:
    # fetch + rebase onto upstream; tolerate "no remote commits" on empty/new repos
    result = _run(cfg, ["pull", "--rebase", "--autostash"], check=False)
    if result.returncode == 0:
        return
    err = (result.stderr or "") + (result.stdout or "")
    if "There is no tracking information" in err or "no upstream" in err.lower():
        return
    if "divergent branches" in err.lower() or "Need to specify" in err:
        # first push case / unset upstream — ignore for pull
        return
    if "CONFLICT" in err or "conflict" in err.lower():
        _run(cfg, ["rebase", "--abort"], check=False)
        raise PushConflictError("Конфликт при pull --rebase — нужен человек")
    # empty repo / nothing to pull
    if "unborn" in err.lower() or "Couldn't find remote ref" in err:
        return
    raise GitError(f"git pull --rebase failed: {err.strip()}")


def add_paths(cfg: Config, paths: list[str | Path]) -> None:
    rels = []
    for p in paths:
        path = Path(p)
        if not path.is_absolute():
            path = cfg.repo_root / path
        try:
            rel = path.resolve().relative_to(cfg.repo_root.resolve())
        except ValueError as exc:
            raise GitError(f"path outside repo: {p}") from exc
        rels.append(str(rel))
    if rels:
        _run(cfg, ["add", "--", *rels])


def commit_with_trailers(
    cfg: Config,
    *,
    subject: str,
    agent: str,
    msg_id: str,
    for_endpoints: list[str],
) -> None:
    body = "\n".join(
        [
            subject,
            "",
            f"Agent: {agent}",
            f"Msg-Id: {msg_id}",
            f"For: {', '.join(for_endpoints)}",
            "",
        ]
    )
    result = _run(cfg, ["commit", "-m", body], check=False)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        if "nothing to commit" in err.lower():
            raise GitError("nothing to commit — stage message/artifact first")
        raise GitError(f"git commit failed: {err}")


def push(cfg: Config) -> bool:
    result = _run(cfg, ["push", "-u", "origin", "HEAD"], check=False)
    if result.returncode == 0:
        return True
    err = (result.stderr or "") + (result.stdout or "")
    if "non-fast-forward" in err or "fetch first" in err.lower() or "rejected" in err.lower():
        return False
    raise GitError(f"git push failed: {err.strip()}")


def push_with_retry(cfg: Config) -> dict:
    """Push; on non-fast-forward, pull --rebase and retry. Escalate on conflict."""
    for _ in range(cfg.push_max_tries):
        if push(cfg):
            return {"ok": True}
        try:
            pull_rebase(cfg)
        except PushConflictError as exc:
            return {"ok": False, "escalated": True, "reason": str(exc)}
    return {
        "ok": False,
        "escalated": True,
        "reason": "push не прошёл после ретраев — нужен человек",
    }
