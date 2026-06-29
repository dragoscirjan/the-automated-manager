# The Automated Manager

An automated tooling suite for team leads and managers to streamline daily operations, communication, and reporting.

## First Tool: Slack Daily Summary (`am slack-summary`)

The `am slack-summary` tool pulls all Slack messages visible to a user for a specified time period (default 24 hours, up to 10 days) and generates a structured summary using an LLM agent CLI.

### Key Features

- **Comprehensive Collection**: Collects public channels, private channels, direct messages (DMs), and group DMs.
- **Thread Support**: Fully resolves and renders threaded conversations recursively.
- **User Name Resolution**: Automatically resolves Slack user IDs to human-readable names.
- **Markdown Export**: Exports raw conversations to clean Markdown files organized by date range.
- **Two Execution Modes**:
  - **Prompt-Only Mode (Default)**: Generates a self-contained prompt containing the exported Slack data and instructions, saving it to `.slack-<period>.prompt.md` for manual use.
  - **Run Mode**: Pipes the prompt directly to an installed agent CLI (OpenCode, Claude Code, Pi.dev, or Copilot CLI) and writes the final summary to a file.

## Quick Start

Run the tool directly via `uvx`:

```bash
uvx --from git+https://github.com/dragoscirjan/the-automated-manager.git am slack-summary --since 24h
```

## Configuration

The tool reads configuration from environment variables or a `.env` file in the current working directory:

```ini
SLACK_USER_TOKEN=xoxp-your-user-token
LLM_PROVIDER=opencode
LLM_MODEL=gpt-4o
AM_TIMEZONE=America/New_York
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
