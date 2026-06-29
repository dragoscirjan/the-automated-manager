# The Automated Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/dragoscirjan/the-automated-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/dragoscirjan/the-automated-manager/actions/workflows/ci.yml)

A growing suite of automation tools for team leads and engineering managers.

The first tool, **`slack-summary`**, pulls every Slack conversation you can see
over a time window (default: the last 24 hours), exports it to Markdown, and
hands it to an LLM **agent CLI** (OpenCode, Claude Code, Pi, or GitHub Copilot
CLI) to produce an executive summary of what happened.

> No LLM API keys are required — the tool shells out to whichever agent CLI you
> already have installed. If you don't pick a provider, it writes a ready-to-use
> prompt instead, so you can paste it into any assistant yourself.

---

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Creating a Slack App & User Token](#creating-a-slack-app--user-token)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Output Layout](#output-layout)
- [Development](#development)
- [License](#license)

---

## Requirements

- **Python 3.11+**
- A Slack **user** OAuth token (`xoxp-…`) — see
  [Creating a Slack App & User Token](#creating-a-slack-app--user-token).
- _(Optional, for automatic summaries)_ one installed agent CLI:
  [`opencode`](https://opencode.ai), [`claude`](https://code.claude.com),
  [`pi`](https://pi.dev), or [`copilot`](https://github.com/github/copilot-cli).

The tool can be run with [`uvx`](https://docs.astral.sh/uv/) without a manual
install.

---

## Quick Start

```bash
# 1. Export your Slack user token (or put it in a .env file — see below)
export SLACK_USER_TOKEN="xoxp-your-token-here"

# 2. Generate a ready-to-paste prompt for the last 24 hours (no provider)
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git \
  am slack-summary

# 3. Or let an installed agent CLI write the summary for you
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git \
  am slack-summary --provider opencode
```

---

## Creating a Slack App & User Token

The tool needs a **user token** (`xoxp-`) so it can read every channel and DM
_you_ can see. Bot tokens only see channels the bot is invited to, which is why
a user token is required.

1. Go to **<https://api.slack.com/apps>** and click **Create New App** →
   **From scratch**.
2. Give it a name (e.g. _Automated Manager_) and pick your workspace.
3. In the left sidebar, open **OAuth & Permissions**.
4. Scroll to **Scopes → User Token Scopes** and add **all** of the following:

   | Scope              | Why                               |
   | ------------------ | --------------------------------- |
   | `channels:read`    | List public channels              |
   | `groups:read`      | List private channels             |
   | `im:read`          | List direct messages              |
   | `mpim:read`        | List group direct messages        |
   | `channels:history` | Read public channel messages      |
   | `groups:history`   | Read private channel messages     |
   | `im:history`       | Read direct messages              |
   | `mpim:history`     | Read group direct messages        |
   | `users:read`       | Resolve user IDs to display names |

5. Scroll back up and click **Install to Workspace**, then **Allow**.
6. Copy the **User OAuth Token** — it starts with `xoxp-`. This is your
   `SLACK_USER_TOKEN`.

> **Keep this token secret.** It grants read access to everything you can see in
> Slack. Store it in an environment variable or a `.env` file that is never
> committed (this repo's `.gitignore` already excludes `.env`).

---

## Configuration

Configuration is read from environment variables, optionally seeded by a `.env`
file. The tool searches for `.env` by walking **up** from your current working
directory, so you can keep a per-project `.env`.

Create a `.env` next to where you run the tool:

```dotenv
# Required: your Slack user OAuth token
SLACK_USER_TOKEN=xoxp-your-token-here

# Optional: default agent CLI provider (opencode | claude | pi | copilot).
# If unset, the tool runs in prompt-only mode.
LLM_PROVIDER=opencode

# Optional: model passed through to the agent CLI (provider-specific).
LLM_MODEL=

# Optional: IANA timezone used for timestamps and the period label.
# Defaults to the system local timezone.
AM_TIMEZONE=Europe/Bucharest
```

| Variable           | Required | Description                                              |
| ------------------ | -------- | -------------------------------------------------------- |
| `SLACK_USER_TOKEN` | yes      | Slack user OAuth token (`xoxp-…`).                       |
| `LLM_PROVIDER`     | no       | Default provider: `opencode`, `claude`, `pi`, `copilot`. |
| `LLM_MODEL`        | no       | Model name forwarded to the agent CLI via `--model`.     |
| `AM_TIMEZONE`      | no       | IANA timezone (e.g. `America/New_York`).                 |

---

## Usage

```text
am slack-summary [OPTIONS]

Options:
  -s, --since TEXT       Time window to summarize, as Nh or Nd (max 10 days).
                         [default: 24h]
  -p, --provider TEXT    Agent CLI to run: opencode | claude | pi | copilot.
                         Overrides LLM_PROVIDER. If omitted and no env default,
                         runs in prompt-only mode.
  -o, --output PATH      Where to write the summary (run mode).
                         [default: summaries/slack-<period>.md]
```

Examples:

```bash
# Last 24 hours, prompt-only (default)
am slack-summary

# Last 3 days, summarized by Claude Code
am slack-summary --since 3d --provider claude

# Last 12 hours to a custom file via OpenCode
am slack-summary -s 12h -p opencode -o reports/today.md
```

### Two modes

- **Prompt-only (default).** When no provider is set, the tool exports your
  Slack data and writes a self-contained prompt to
  `summaries/.slack-<period>.prompt.md`. Paste it into any assistant.
- **Run mode.** With `--provider` (or `LLM_PROVIDER`), the tool inlines the
  exported data into the prompt, runs the agent CLI, captures its output, and
  writes the finished summary to the `--output` path.

The time window accepts `Nh` (hours) or `Nd` (days), e.g. `24h`, `12h`, `7d`.
The maximum span is **10 days**.

---

## How It Works

1. Resolve the time window and timezone.
2. List every conversation you can see (public + private channels, DMs, and
   group DMs), skipping archived and empty ones.
3. Fetch messages and thread replies within the window, resolving user mentions
   to display names. Rate limits are retried automatically.
4. Render each conversation to Markdown under `slack/<period>/`.
5. Either build a prompt (prompt-only) or run your chosen agent CLI and write
   the summary (run mode).

---

## Output Layout

```text
.
├── slack/
│   └── 2026-06-29/                  # period label (single day or range)
│       ├── channel-general.md
│       ├── channel-incidents.md
│       └── dm-jane-doe.md
└── summaries/
    ├── slack-2026-06-29.md          # run mode: the finished summary
    └── .slack-2026-06-29.prompt.md  # prompt-only mode: paste-ready prompt
```

The period label is `YYYY-MM-DD` for a single day, or
`YYYY-MM-DD-YYYY-MM-DD` for a multi-day window.

---

## Development

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full developer workflow.

```bash
# Install toolchain (mise: python, node, uv) and dependencies
mise install
mise exec -- uv sync

# Run the test suite
mise exec -- uv run pytest -q

# Lint, format, build, test — the full gate
task validate
```

---

## License

[MIT](./LICENSE) © Dragos Cirjan
