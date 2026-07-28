# A2A-over-git

Координация агентов проектной команды через общий git-репозиторий.

- Протокол: [`.agents/PROTOCOL.md`](.agents/PROTOCOL.md)
- Привязка для агентов: [`AGENTS.md`](AGENTS.md)
- MCP-сервер (Python stdio): пакет `mcp_a2a/`
- Cursor MCP: [`.cursor/mcp.json`](.cursor/mcp.json) (в репо, без identity)

## Быстрый старт

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# идентичность — только локально, не в git (§3):
mkdir -p .git/agents
echo analyst-agent > .git/agents/whoami   # или manager-agent

./scripts/run-a2a-mcp.sh
```

Инструменты: `post_message`, `read_inbox`, `get_thread`, `pending`, `mark_processed`, `whoami`.

## Cursor IDE

Открой **этот клон** как корень workspace. Project MCP (`.cursor/mcp.json`) общий для всех;
кто ты — читается из `.git/agents/whoami`.
