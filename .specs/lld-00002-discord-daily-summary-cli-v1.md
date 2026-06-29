---
id: "00002"
type: lld
title: "Discord Daily Summary CLI"
version: 1
status: draft
parent: "00001"
opencode-agent: lead-engineer
---

# Discord Daily Summary CLI

## 1. Overview

Add a second CLI tool to The Automated Manager:

- `am discord-summary`

The command collects Discord messages visible to a configured bot for a time
window (default `24h`, max `10d`), exports one Markdown file per conversation
under `./discord/<period>/`, then:

- prompt-only mode (default): writes a prompt file for manual agent execution
- run mode: invokes existing provider CLIs (`opencode|claude|pi|copilot`) and
  writes summary output

This mirrors Slack behavior, including period naming and summary output layout,
but with `discord` prefixes.

## 2. Goals / Non-Goals

### Goals

- Same UX and time parsing behavior as `am slack-summary`
- Collect all readable Discord conversations by default, with optional include
  filter via CLI argument
- Include guild text channels + threads, plus DM/private channels visible to bot
- Reuse existing LLM provider abstraction and prompt-vs-run model
- Output layout:
  - data export: `discord/<period>/...`
  - summary default: `summaries/discord-<period>.md`

### Non-Goals

- No Discord posting/replying (read-only)
- No persistent database
- No self-bot/user-token scraping

## 3. Required Config

Add new env var:

- `DISCORD_BOT_TOKEN` (required for `discord-summary` only)

Keep existing:

- `LLM_PROVIDER`, `LLM_MODEL`, `AM_TIMEZONE`

Settings refactor:

- `slack_user_token` becomes optional at model level
- `discord_bot_token` added optional
- command-specific validation in orchestration layer raises `ConfigError` when
  required token for chosen command is missing

This avoids forcing Slack token when user runs only Discord command.

## 4. CLI Design

New command:

```bash
am discord-summary \
  --since 24h \
  --provider opencode \
  --output summaries/discord-2026-06-29.md \
  --include guild_text,thread,dm,group_dm
```

Options:

- `--since/-s` (same parser: `Nh|Nd`, default `24h`, max `10d`)
- `--provider/-p` same as Slack
- `--output/-o` same as Slack, default `summaries/discord-<period>.md`
- `--include` comma list, default all: `guild_text,thread,dm,group_dm`

Exit codes unchanged:

- `0` success
- `1` runtime/config/provider/API errors
- `2` validation errors

## 5. Package / File Changes

Add:

```text
src/automated_manager/discord/
  __init__.py
  client.py
  collector.py
  render.py
src/automated_manager/discord_summary.py
tests/discord_test.py
tests/discord_summary_test.py
```

Update:

- `src/automated_manager/config.py` (optional token model + discord token)
- `src/automated_manager/cli.py` (new command)
- `README.md` (Discord setup + usage)
- `pyproject.toml` runtime deps (add `discord.py`)

## 6. Discord Collection Approach

Library:

- `discord.py` (MIT), using gateway login for readable channel traversal

Client responsibilities (`discord/client.py`):

- initialize `discord.Client` with required intents (`guilds`, `messages`,
  `message_content`, `dm_messages`)
- connect, wait ready, expose read APIs, clean shutdown

Collector (`discord/collector.py`):

- enumerate accessible guild text channels + threads
- enumerate accessible DM/group DM channels available to bot session
- fetch history within `[oldest, latest]`
- map author IDs to display names
- skip empty conversations
- normalize into immutable domain model (DiscordConversation/DiscordMessage)

## 7. Rendering / Prompt / Summary

Renderer (`discord/render.py`):

- one markdown file per conversation in `discord/<period>/`
- similar structure to Slack markdown, with channel/conversation title, message
  timeline, nested thread replies where available

Summary orchestration (`discord_summary.py`):

- same flow as Slack orchestration:
  1. resolve period
  2. collect
  3. write exports
  4. build prompt (reuse `llm.prompt.build_prompt`)
  5. run provider OR write `.discord-<period>.prompt.md`

## 8. Documentation Updates

README additions:

- Discord bot creation steps
- required intents and read permissions
- token setup (`DISCORD_BOT_TOKEN`)
- command examples for prompt mode and run mode
- output layout examples for `discord/<period>/`

## 9. Testing Plan

- `tests/discord_test.py`
  - include-filter behavior
  - channel/message normalization
  - empty-channel skip
  - period boundary filtering
- `tests/discord_summary_test.py`
  - prompt-only mode writes `.discord-<period>.prompt.md`
  - run mode writes summary output via mocked provider
  - missing `DISCORD_BOT_TOKEN` -> `ConfigError`
- `tests/cli_test.py`
  - add `discord-summary` command path and exit-code assertions

## 10. Risks / Constraints

- Discord private-message visibility is limited to channels visible to the bot
  (not arbitrary user account inbox access).
- Message content requires proper intent configuration in the Discord Developer
  Portal.
- Large exports may create long prompts; current provider execution remains
  argv-based (future optimization: stdin/temp-file fallback if needed).

## 11. Build Order

1. Config refactor + dependency update (`discord.py`)
2. Discord client/collector + render modules
3. Discord summary orchestration
4. CLI integration (`am discord-summary`)
5. Tests (unit + CLI)
6. README updates
7. Quality gate (`task validate`) + issue/status updates
