"""Identity and runtime config. Identity never comes from the model."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    identity: str
    repo_root: Path
    max_depth: int
    endpoints: frozenset[str]
    push_max_tries: int = 5

    @property
    def participant_id(self) -> str:
        for suffix in ("-agent", "-human"):
            if self.identity.endswith(suffix):
                return self.identity[: -len(suffix)]
        raise ValueError(f"identity must end with -agent or -human: {self.identity!r}")

    @property
    def human_owner(self) -> str:
        return f"{self.participant_id}-human"

    @property
    def msgs_dir(self) -> Path:
        return self.repo_root / ".agents" / "msgs"

    @property
    def archive_dir(self) -> Path:
        return self.repo_root / ".agents" / "archive"

    @property
    def agents_local_dir(self) -> Path:
        return self.repo_root / ".git" / "agents"

    @property
    def cursor_path(self) -> Path:
        return self.agents_local_dir / f"{self.identity}.cursor"


def _read_whoami(repo_root: Path) -> str | None:
    path = repo_root / ".git" / "agents" / "whoami"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def _load_endpoints(repo_root: Path) -> frozenset[str]:
    path = repo_root / ".agents" / "participants.json"
    if not path.is_file():
        return frozenset()
    data = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(data.get("endpoints", []))


def load_config(
    identity: str | None = None,
    repo_root: str | Path | None = None,
    max_depth: int | None = None,
) -> Config:
    root = Path(repo_root or os.environ.get("A2A_REPO_ROOT") or os.getcwd()).resolve()
    ident = identity or os.environ.get("A2A_IDENTITY") or _read_whoami(root)
    if not ident:
        raise RuntimeError(
            "A2A identity not set. Export A2A_IDENTITY or write .git/agents/whoami"
        )
    depth = max_depth
    if depth is None:
        depth = int(os.environ.get("A2A_MAX_DEPTH", "10"))
    endpoints = _load_endpoints(root)
    if ident not in endpoints and endpoints:
        raise RuntimeError(
            f"identity {ident!r} is not in .agents/participants.json endpoints"
        )
    return Config(
        identity=ident,
        repo_root=root,
        max_depth=depth,
        endpoints=endpoints,
    )
