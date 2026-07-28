"""Unit tests for message validation and obligation fold (no network)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mcp_a2a.config import Config
from mcp_a2a import messages as msg_mod


def _cfg(tmp: Path) -> Config:
    (tmp / ".agents" / "msgs").mkdir(parents=True)
    (tmp / ".agents" / "participants.json").write_text(
        json.dumps(
            {
                "endpoints": [
                    "analyst-agent",
                    "analyst-human",
                    "manager-agent",
                    "manager-human",
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp / ".git" / "agents").mkdir(parents=True)
    return Config(
        identity="manager-agent",
        repo_root=tmp,
        max_depth=10,
        endpoints=frozenset(
            [
                "analyst-agent",
                "analyst-human",
                "manager-agent",
                "manager-human",
            ]
        ),
    )


class ObligationTests(unittest.TestCase):
    def test_fold_closes_question_with_answer(self) -> None:
        msgs = [
            {
                "id": "a1",
                "ts": "2026-07-28T14:00:00Z",
                "from": "analyst-agent",
                "to": ["manager-agent"],
                "type": "question",
                "in_reply_to": None,
                "root": "a1",
                "refs": {},
                "body": "Сколько дней на 4.2?",
            },
            {
                "id": "b2",
                "ts": "2026-07-28T14:01:00Z",
                "from": "manager-agent",
                "to": ["analyst-agent"],
                "type": "answer",
                "in_reply_to": "a1",
                "root": "a1",
                "refs": {},
                "body": "5",
            },
        ]
        obs = msg_mod.fold_obligations(msgs)
        self.assertEqual(len(obs), 1)
        self.assertFalse(obs[0]["open"])
        self.assertEqual(obs[0]["closed_by"], "b2")

    def test_answer_rejects_wrong_parent(self) -> None:
        with self.assertRaises(msg_mod.ProtocolError):
            msg_mod.validate_response_type("inform", "answer")

    def test_propose_must_target_human(self) -> None:
        with self.assertRaises(msg_mod.ProtocolError):
            msg_mod.validate_propose_addressee("propose", ["manager-agent"])
        msg_mod.validate_propose_addressee("propose", ["manager-human"])

    def test_write_and_find(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg = _cfg(tmp)
            msg = {
                "id": "a1b2c3d4",
                "ts": "2026-07-28T14:30:00Z",
                "from": "analyst-agent",
                "to": ["manager-agent"],
                "type": "inform",
                "in_reply_to": None,
                "root": "a1b2c3d4",
                "refs": {"files": ["wbs.csv"], "locator": "row 4.2"},
                "body": "test",
            }
            path = msg_mod.write_msg(cfg, msg)
            self.assertTrue(path.is_file())
            found = msg_mod.find_msg(cfg, "a1b2c3d4")
            self.assertEqual(found["body"], "test")


if __name__ == "__main__":
    unittest.main()
