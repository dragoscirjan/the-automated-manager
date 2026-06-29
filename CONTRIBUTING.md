# Contributing to The Automated Manager

Thanks for your interest in improving the project! This guide covers the
developer workflow, tooling, and conventions.

## Ways to Contribute

- Reporting bugs
- Discussing the current state of the code
- Submitting fixes and new features
- Proposing new automation tools

## Development Setup

The project uses [`mise`](https://mise.jdx.dev) to pin the toolchain
(Python 3.11, Node, and [`uv`](https://docs.astral.sh/uv/)) and
[`Task`](https://taskfile.dev) as the task runner.

```bash
# 1. Install the pinned toolchain
mise install

# 2. Install Python dependencies (creates .venv)
mise exec -- uv sync

# 3. Install Node dev tooling (prettier, eslint, jscpd, husky, lint-staged)
npm install
```

## Project Layout

```text
src/automated_manager/
├── cli.py            # Typer entrypoint (`am`)
├── config.py         # pydantic-settings; loads .env from cwd
├── errors.py         # typed exception hierarchy → exit codes
├── timeparse.py      # Nh/Nd window parsing + Period model
├── summarize.py      # orchestration (collect → export → summarize)
├── slack/            # Slack Web API client, collector, Markdown renderer
└── llm/              # agent-CLI providers + prompt builder
tests/                # pytest suite (*_test.py)
```

## Common Tasks

All quality operations are exposed through `Task`:

```bash
task test            # run pytest
task lint            # ruff + pylint + eslint + prettier checks
task format          # auto-format (ruff, prettier)
task build           # uv build (wheel + sdist)
task duplicate-check # jscpd copy-paste detection
task validate        # format → build → lint → run → test → docs (full gate)
```

You can also run tools directly:

```bash
mise exec -- uv run pytest -q
mise exec -- uv run am slack-summary --help
```

## Coding Standards

- **Style:** [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) (PEP 8).
- **Typing:** type hints are mandatory; `mypy` must pass.
- **Linting/formatting:** `ruff` (format + lint) and `pylint`.
- **Errors:** raise the typed exceptions in `errors.py`; use `raise ... from err`.
  Never swallow exceptions or use bare `except:`.
- **Tests:** every module ships with `tests/<name>_test.py`. Mock external I/O
  (Slack API, agent-CLI subprocesses) — tests must not hit the network or run
  real CLIs.

## Adding a New LLM Provider

1. Create `src/automated_manager/llm/<name>.py` subclassing `AgentProvider`.
2. Set the `name` class attribute and implement `_command(prompt)` to return the
   argument list for the CLI (the prompt is passed as a command-line argument;
   stdout is captured as the summary).
3. Register it in `llm/__init__.py`'s `_PROVIDERS` map.
4. Add a test covering `_command` construction.

## Commit & PR Workflow

1. Branch off `main` (e.g. `feat/<short-name>` or `fix/<short-name>`).
2. Keep commits focused; follow conventional-commit style where practical.
3. Run `task validate` before pushing — it must pass.
4. Open a PR describing the change and linking any related issue.
5. **Do not merge without maintainer approval.**

## License

By contributing, you agree that your contributions will be licensed under the
project's [MIT License](./LICENSE).
