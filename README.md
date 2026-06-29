# The Automated Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/dragoscirjan/the-automated-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/dragoscirjan/the-automated-manager/actions/workflows/ci.yml)

A growing suite of automation tools for team leads and engineering managers.

Current commands:

- `am slack-summary` (Slack user-token workflow)
- `am discord-summary` (Discord bot-token workflow)

Both commands collect messages for a time window, export one Markdown file per
conversation, then either:

- write a ready-to-paste prompt (default), or
- run an installed agent CLI (`opencode`, `claude`, `pi`, `copilot`) and write
  the final summary.

## Requirements

- Python 3.11+
- Slack user OAuth token (`xoxp-...`) for `slack-summary`
- Discord bot token for `discord-summary`
- Optional agent CLI for run mode (`opencode`, `claude`, `pi`, `copilot`)

## Quick Start

```bash
# Configure tokens
export SLACK_USER_TOKEN="xoxp-your-token"
export DISCORD_BOT_TOKEN="your-discord-bot-token"

# Prompt-only mode (default)
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git am slack-summary
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git am discord-summary

# Run mode using an installed provider
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git am slack-summary --provider opencode
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git am discord-summary --provider opencode
```

## Slack App Setup (User Token)

1. Create app at https://api.slack.com/apps
2. In OAuth & Permissions -> User Token Scopes, add:
   - channels:read
   - groups:read
   - im:read
   - mpim:read
   - channels:history
   - groups:history
   - im:history
   - mpim:history
   - users:read
3. Install app to workspace and copy `xoxp-...` token
4. Set `SLACK_USER_TOKEN`

## Discord App Setup (Bot Token)

1. Create app at https://discord.com/developers/applications
2. Add a bot in the Bot tab
3. Enable Message Content Intent
4. Copy bot token and set `DISCORD_BOT_TOKEN`
5. Invite bot with read permissions to target servers/channels

## Configuration

Configuration is loaded from environment or a `.env` discovered by walking up
from current working directory.

```dotenv
SLACK_USER_TOKEN=xoxp-your-token
DISCORD_BOT_TOKEN=your-discord-bot-token
LLM_PROVIDER=opencode
LLM_MODEL=
AM_TIMEZONE=Europe/Bucharest
```

Token requirements are command-specific:

- `am slack-summary` -> requires `SLACK_USER_TOKEN`
- `am discord-summary` -> requires `DISCORD_BOT_TOKEN`

## Usage

```text
am slack-summary [OPTIONS]
am discord-summary [OPTIONS]

Common options:
  -s, --since TEXT       Nh or Nd, default 24h, max 10d
  -p, --provider TEXT    opencode | claude | pi | copilot
  -o, --output PATH      summary output path

Discord-only:
      --include TEXT     comma list: guild_text,thread,dm,group_dm
```

Examples:

```bash
am slack-summary --since 3d
am discord-summary --since 12h --include guild_text,thread
am discord-summary --provider claude -o reports/discord.md
```

## Output Layout

```text
.
├── slack/
│   └── <period>/
│       └── *.md
├── discord/
│   └── <period>/
│       └── *.md
└── summaries/
    ├── slack-<period>.md
    ├── .slack-<period>.prompt.md
    ├── discord-<period>.md
    └── .discord-<period>.prompt.md
```

`<period>` is `YYYY-MM-DD` for single-day windows or
`YYYY-MM-DD-YYYY-MM-DD` for ranges.

## Development

```bash
mise install
mise exec -- uv sync
npm install
task validate
```

## License

MIT
