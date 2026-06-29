---
id: "00001"
type: lld
title: "Slack Daily Summary CLI"
version: 1
status: draft
opencode-agent: lead-engineer
---

# Slack Daily Summary CLI

## 1. Overview

First tool of "the automated manager" suite. Pulls all Slack messages visible to a
user over a time window (default 24h, max 10d), exports them as Markdown, then
either (a) emits a ready-to-paste prompt referencing the exported data, or (b)
shells out to an installed agent CLI to produce a summary.

Runs via `uvx`, reads secrets from a `.env` file (auto-detected from cwd) or env vars.

**Entry point:** `am slack-summary [OPTIONS]`
**uvx:** `uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git am slack-summary`

## 2. Goals & Non-Goals

**Goals**

- Collect public channels, private channels, DMs (im), group DMs (mpim) visible to the user.
- Export one Markdown file per conversation under `./slack/<period>/`.
- Resolve user/channel IDs to human-readable names.
- Produce a summary via an agent CLI (OpenCode, Claude Code, Pi.dev, Copilot CLI) OR emit a prompt.
- Repurpose the existing Bash/PowerShell template repo into a clean Python CLI app.

**Non-Goals**

- No LLM API keys (Anthropic/OpenAI). Summarization is delegated to installed agent CLIs.
- No posting back to Slack (v1).
- No persistent database; filesystem export only.

## 3. Package Structure

`src/` layout, package `automated_manager`:

```
src/automated_manager/
  __init__.py
  __main__.py            # `python -m automated_manager`
  cli.py                 # Typer app; command: slack-summary
  config.py              # pydantic-settings; loads .env from cwd + env vars
  errors.py              # typed exceptions (ConfigError, SlackError, ProviderError)
  timeparse.py           # parse Nh/Nd -> timedelta; period -> dir name
  slack/
    __init__.py
    client.py            # thin slack_sdk WebClient wrapper + pagination + rate-limit retry
    collector.py         # orchestrates conversations.list/history/replies + user resolution
    render.py            # messages -> Markdown (one file per conversation)
  llm/
    __init__.py
    base.py              # Provider protocol + registry
    prompt.py            # builds the summarization prompt (references data dir + output path)
    opencode.py          # opencode run "<prompt>"
    claude.py            # claude -p "<prompt>"  (stdin pipe)
    pi.py                # pi -p "<prompt>"
    copilot.py           # copilot -p "<prompt>"
  summarize.py           # top-level orchestration: collect -> render -> (prompt | run)
tests/
  test_timeparse.py
  test_render.py
  test_config.py
  test_prompt.py
  test_cli.py            # Typer CliRunner
```

## 4. Configuration (`config.py`)

`pydantic-settings` `BaseSettings`, `.env` discovered from cwd (walk up to git root / fs root).

| Setting      | Env var            | Default            | Notes                                          |
| ------------ | ------------------ | ------------------ | ---------------------------------------------- |
| slack_token  | `SLACK_USER_TOKEN` | (required)         | `xoxp-` user OAuth token                       |
| llm_provider | `LLM_PROVIDER`     | `""` (prompt-only) | one of: opencode, claude, pi, copilot          |
| llm_model    | `LLM_MODEL`        | `""`               | optional, passed to provider `--model`         |
| timezone     | `AM_TIMEZONE`      | system local       | IANA name; used for period naming + timestamps |

Missing `SLACK_USER_TOKEN` -> `ConfigError` with guidance pointing to README setup.

## 5. CLI (`cli.py`)

```
am slack-summary
  --since TEXT        # default "24h"; format Nh|Nd; max 10d (240h). Invalid/over -> exit 2
  --provider TEXT     # overrides LLM_PROVIDER; empty => prompt-only mode
  --model TEXT        # overrides LLM_MODEL
  --output PATH       # default summaries/slack-<period>.md
  --data-dir PATH     # default slack/<period>/
  --include TEXT      # comma list of types; default public,private,im,mpim
  --dry-run           # collect + render only; skip summary/prompt
  -v/--verbose
```

Exit codes: `0` ok, `1` runtime (Slack/provider) error, `2` usage/validation error.

## 6. Time Window (`timeparse.py`)

- Parse `^(\d+)([hd])$`; reject otherwise (exit 2).
- Enforce max 240h / 10d.
- `oldest` = now - delta; `latest` = now.
- **Period dir name:** if the window spans a single calendar day (in configured TZ) -> `YYYY-MM-DD`; else `YYYY-MM-DD-YYYY-MM-DD` (start-end). Used for both `slack/<period>/` and default output `summaries/slack-<period>.md`.

## 7. Slack Collection

**slack_sdk `WebClient`** (runtime dep `slack-sdk`).

User-token OAuth scopes (documented in README for app creation):
`channels:read, groups:read, im:read, mpim:read, channels:history, groups:history, im:history, mpim:history, users:read`.

Flow:

1. `users.list` (paginated) -> build `{user_id: display_name}` map once.
2. `conversations.list` with `types=public_channel,private_channel,mpim,im`, `exclude_archived=true`, cursor pagination -> conversations.
3. For each conversation: `conversations.history` with `oldest`/`latest`, cursor pagination.
4. For messages with `thread_ts` and `reply_count>0`: `conversations.replies` to pull thread.
5. Resolve channel name (`name` for channels; for `im` resolve peer user display name; for `mpim` use member list).

**Rate limiting:** respect HTTP 429 `Retry-After`; bounded exponential backoff (max ~5 retries). `slack_sdk` exposes this; wrap in `client.py`.

**Empty windows:** conversations with zero messages in range are skipped (no file).

## 8. Markdown Render (`render.py`)

One file per conversation: `slack/<period>/<safe-channel-name>.md`.

```
# <#channel-name | DM with Alice | Group: a, b, c>

> Period: <oldest ISO> - <latest ISO> (<TZ>)

## <YYYY-MM-DD HH:MM> Alice
message text (user IDs <@U...> resolved to @names)

  ↳ <HH:MM> Bob (thread reply)
  thread text
```

- Chronological; thread replies indented under parent.
- `<@U…>` mentions and `<#C…>` channel refs resolved to names.
- Filenames sanitized (`[^a-z0-9-_]` -> `-`), deduped with numeric suffix.

## 9. Summarization (`llm/`)

**Prompt (`prompt.py`)** — single template that includes:

- Role: "summarize what happened across these Slack conversations for a team lead".
- The exported data dir path and the `--output` target path.
- Instructions: group by channel, surface decisions/action items/blockers/@mentions of me, keep it skimmable.

**Mode A — prompt-only (default, no provider):**
Render the prompt to `summaries/.slack-<period>.prompt.md` and print it + the data-dir path to stdout. User pastes into their interactive harness (which has file access).

**Mode B — run (provider set):**
Inline the rendered Markdown data into the prompt (stdin) and invoke the CLI in print mode; capture **stdout**; write to `--output`. We own the file write (uniform across tools, sidesteps Copilot `--allow-tool=write`).

| Provider | Invocation (conceptual)                    |
| -------- | ------------------------------------------ |
| opencode | `opencode run "<prompt+data>"` [`--model`] |
| claude   | `<prompt+data>` piped to `claude -p`       |
| pi       | `pi -p "<prompt+data>"`                    |
| copilot  | `<prompt+data>` piped to `copilot -p`      |

`base.Provider` protocol: `name`, `is_available()` (shutil.which), `summarize(prompt, data, model) -> str`. Unknown provider or missing binary -> `ProviderError` listing installed options.

Implemented with `subprocess.run` (list args, no `shell=True`), timeout, captured stdout/stderr; non-zero exit -> `ProviderError` with stderr tail.

## 10. Repo Repurposing (config rewiring)

The cleanup (staged, uncommitted) removed all shell/PowerShell demo code & tooling. These dangling references must be rewired so the repo is valid:

- **pyproject.toml**: name `automated-manager`; `requires-python>=3.11`; runtime deps `slack-sdk`, `pydantic-settings`, `typer`, `python-dotenv`; `[project.scripts] am = "automated_manager.cli:app"`; `[tool.hatch.build.targets.wheel] packages=["src/automated_manager"]`; pylint `source-roots=["src"]`; pytest `testpaths=["tests"]`; ruff isort `known-first-party=["automated_manager"]`. Keep black/ruff/pylint/mypy/pytest/mkdocs dev deps.
- **mise.toml**: remove `[tools."github:PowerShell/PowerShell"]`, `[tools."github:koalaman/shellcheck"]` (+ their platform blocks) and the `[hooks] postinstall` (fix-mise-pwsh). Keep node, python=3.11, uv.
- **package.json**: drop `bats` devDep. Keep jscpd/eslint/prettier/husky/lint-staged (lint json/yaml/md only).
- **Taskfile.yml**: remove `shlint_py`/`pwshlint_py` + bats/pester tasks; repoint `run`->`am`, `build`->`uv build`, `test`->`pytest`; keep `validate` chain (format/lint/test/build/docs).
- **.taskfiles/Taskfile.quality.yml**: remove pwshlint/shlint tasks and their refs in aggregated `lint`/`lint:check`. Keep prettier/eslint/ruff/pylint/duplicate-check.
- **.lintstagedrc.yml**: replace `task pwshlint_py`/`task shlint_py` entries with Python (`*.py` -> ruff/black) and keep json/yaml/md -> prettier.
- **README.md**: full rewrite — what the tool does, Slack app + scopes setup, `.env` keys, `uvx` usage, the two summary modes, examples.

## 11. Dependencies

Runtime: `slack-sdk`, `pydantic-settings`, `python-dotenv`, `typer`.
Dev (existing): `pytest`, `ruff`, `black`, `pylint`, `mypy`, `mkdocs(+material,mkdocstrings)`.

## 12. Testing

- `timeparse`: valid/invalid formats, max bound, single-day vs range naming (freeze time + TZ).
- `render`: mention resolution, thread indentation, filename sanitization, empty skip.
- `config`: env precedence, `.env` discovery, missing-token error.
- `prompt`: contains data-dir + output path.
- `cli`: Typer `CliRunner` — `--dry-run`, validation exit codes, prompt-only vs run (provider mocked via `subprocess`).
- Slack client paginated/rate-limit paths mocked (no live API in unit tests).

## 13. Open Risks

- Slack rate limits on large workspaces (many conversations) — mitigated by backoff; may be slow. Acceptable for v1.
- Agent CLI output formats vary; we treat stdout as the summary verbatim. Document expectation.
- `im`/`mpim` history scopes require the user token to actually be a member; bot tokens explicitly unsupported.

## 14. Build Order (tasks)

1. Rewire repo configs (pyproject, mise, package.json, Taskfiles, lint-staged) + scaffold `src/automated_manager/` package skeleton.
2. `timeparse.py` + tests.
3. `config.py` + tests.
4. `slack/client.py` + `collector.py` + `render.py` + tests (mocked).
5. `llm/` providers + `prompt.py` + tests.
6. `summarize.py` + `cli.py` + CLI tests.
7. README rewrite + Slack app setup docs.
8. Quality gate (`task validate`) + code review.
