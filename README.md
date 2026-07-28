# A2A-over-git

Координация агентов проектной команды через общий git-репозиторий.

- Протокол: [`.agents/PROTOCOL.md`](.agents/PROTOCOL.md)
- Привязка для агентов: [`AGENTS.md`](AGENTS.md)
- MCP-сервер (Python stdio): пакет `mcp_a2a/`
- Cursor MCP: [`.cursor/mcp.json`](.cursor/mcp.json) (в репо, без identity)

## Быстрый старт

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows (cmd):  .venv\Scripts\activate.bat
# Windows (PowerShell):  .venv\Scripts\Activate.ps1

python -m pip install -r requirements.txt

# идентичность — только локально, не в git (§3):
mkdir -p .git/agents                 # Windows: mkdir .git\agents
echo analyst-agent > .git/agents/whoami   # или manager-agent

python -m mcp_a2a
```

Инструменты: `post_message`, `read_inbox`, `get_thread`, `pending`, `mark_processed`, `whoami`.

## Cursor IDE

1. Открой **этот клон** как корень workspace.
2. Выбери интерпретатор проекта: `.venv` (`Python: Select Interpreter`).
3. Project MCP (`.cursor/mcp.json`) общий: `python -m mcp_a2a`.
4. Кто ты — из `.git/agents/whoami` (не из mcp.json).

## Ручная правка + пуш через A2A

Общие артефакты (`wbs.csv` и т.п.) можно править руками. Не коммить и не пушь их отдельно через `git` — публикация идёт через MCP `post_message` (сервер коммитит сообщение вместе с артефактом и делает push). Файлы в `.agents/msgs/` руками не трогай.

После правки достаточно сказать агенту:

> запушь через a2a

Агент сам смотрит `git status` / `git diff`, подставляет изменённые файлы в `refs`, выбирает тип и адресата по роли (для аналитика при смене WBS — обычно `inform` на `manager-agent`) и вызывает `post_message`. Указывать путь к файлу в фразе не обязательно.
