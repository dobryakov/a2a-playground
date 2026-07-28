# A2A-over-git

Координация агентов проектной команды через общий git-репозиторий.

- Протокол: [`.agents/PROTOCOL.md`](.agents/PROTOCOL.md)
- Привязка для агентов: [`AGENTS.md`](AGENTS.md)
- MCP-сервер (Python stdio): пакет `mcp_a2a/`

## Быстрый старт

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# идентичность — только локально (env или .git/agents/whoami)
export A2A_IDENTITY=analyst-agent
export A2A_REPO_ROOT="$(pwd)"

.venv/bin/python -m mcp_a2a
```

Пример конфига MCP-клиента (Cursor / Claude Code):

```json
{
  "mcpServers": {
    "a2a-over-git": {
      "command": "/path/to/clone/.venv/bin/python",
      "args": ["-m", "mcp_a2a"],
      "cwd": "/path/to/clone",
      "env": {
        "A2A_IDENTITY": "analyst-agent",
        "A2A_REPO_ROOT": "/path/to/clone"
      }
    }
  }
}
```

Инструменты: `post_message`, `read_inbox`, `get_thread`, `pending`, `mark_processed`.

## Cursor IDE

Скопируй `.cursor/mcp.json.example` → `.cursor/mcp.json`, подставь путь к клону и свой `A2A_IDENTITY`
(`analyst-agent` / `manager-agent`). Файл `mcp.json` в git не коммитится (идентичность локальная).
Открой **этот клон** как корень workspace, чтобы подхватились project MCP и `AGENTS.md`.
