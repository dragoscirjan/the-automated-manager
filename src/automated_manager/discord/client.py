"""Thin Discord client for collecting message history in a time window."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..errors import DiscordCollectionError
from ..timeparse import Period

if TYPE_CHECKING:
    import discord

try:  # pragma: no cover - import behavior covered indirectly
    import discord
except ImportError:  # pragma: no cover
    discord = None  # type: ignore[assignment]

_ALL_KINDS = frozenset({"guild_text", "thread", "dm", "group_dm"})


@dataclass(frozen=True)
class RawMessage:
    """Raw Discord message payload produced by :class:`DiscordClient`."""

    ts: str
    author: str
    text: str


@dataclass(frozen=True)
class RawConversation:
    """Raw Discord conversation payload produced by :class:`DiscordClient`."""

    id: str
    title: str
    kind: str
    messages: tuple[RawMessage, ...]


class DiscordClient:
    """Collect readable Discord conversations for a period via ``discord.py``."""

    def __init__(self, token: str) -> None:
        self._token = token

    def collect(
        self,
        period: Period,
        include_kinds: set[str] | None = None,
    ) -> list[RawConversation]:
        """Collect readable conversations for ``period`` and selected kinds."""
        if discord is None:
            raise DiscordCollectionError(
                "discord.py is not installed. Install dependencies and retry."
            )

        kinds = include_kinds or set(_ALL_KINDS)
        unknown = kinds - _ALL_KINDS
        if unknown:
            names = ", ".join(sorted(unknown))
            raise DiscordCollectionError(
                f"Unknown Discord include kinds: {names}. "
                "Allowed: guild_text, thread, dm, group_dm."
            )

        try:
            return asyncio.run(self._collect_async(period, kinds))
        except RuntimeError as err:
            raise DiscordCollectionError(
                "Discord collection cannot run inside an active event loop."
            ) from err

    async def _collect_async(
        self,
        period: Period,
        include_kinds: set[str],
    ) -> list[RawConversation]:
        client = discord.Client(intents=_intents())
        ready = asyncio.Event()

        @client.event
        async def on_ready() -> None:  # pragma: no cover - event callback
            ready.set()

        task = asyncio.create_task(client.start(self._token))
        ready_task = asyncio.create_task(ready.wait())

        try:
            done, _ = await asyncio.wait(
                {task, ready_task},
                timeout=20,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if ready_task not in done:
                if task.done():
                    task.result()
                raise DiscordCollectionError(
                    "Timed out waiting for Discord client readiness. "
                    "Verify token and intents."
                )
            return await self._collect_conversations(client, period, include_kinds)
        except DiscordCollectionError:
            raise
        except Exception as err:
            raise DiscordCollectionError(
                "Unable to connect to Discord. Verify DISCORD_BOT_TOKEN and bot intents."
            ) from err
        finally:
            await client.close()
            ready_task.cancel()
            task.cancel()
            with suppress(asyncio.CancelledError):
                await ready_task
            with suppress(asyncio.CancelledError):
                await task

    async def _collect_conversations(
        self,
        client: "discord.Client",
        period: Period,
        include_kinds: set[str],
    ) -> list[RawConversation]:
        conversations: list[RawConversation] = []
        if "guild_text" in include_kinds:
            for guild in client.guilds:
                await self._collect_channel_group(
                    conversations,
                    guild.text_channels,
                    "guild_text",
                    period,
                )

        if "thread" in include_kinds:
            for guild in client.guilds:
                await self._collect_channel_group(
                    conversations,
                    guild.threads,
                    "thread",
                    period,
                )

        await self._collect_private_channels(
            conversations, client, include_kinds, period
        )
        return conversations

    async def _collect_channel_group(
        self,
        out: list[RawConversation],
        channels: list[object],
        kind: str,
        period: Period,
    ) -> None:
        """Collect one homogeneous channel group into ``out``."""
        for channel in channels:
            conversation = await self._from_channel(channel, kind, period)
            if conversation is not None:
                out.append(conversation)

    async def _collect_private_channels(
        self,
        out: list[RawConversation],
        client: "discord.Client",
        include_kinds: set[str],
        period: Period,
    ) -> None:
        """Collect DM and group DM conversations visible to the bot."""
        for private_channel in client.private_channels:
            kind: str | None = None
            if isinstance(private_channel, discord.DMChannel) and "dm" in include_kinds:
                kind = "dm"
            if (
                isinstance(private_channel, discord.GroupChannel)
                and "group_dm" in include_kinds
            ):
                kind = "group_dm"
            if not kind:
                continue
            conversation = await self._from_channel(private_channel, kind, period)
            if conversation is not None:
                out.append(conversation)

    async def _from_channel(
        self,
        channel: object,
        kind: str,
        period: Period,
    ) -> RawConversation | None:
        """Read one channel history in the selected period."""
        title = self._title(channel, kind)
        messages: list[RawMessage] = []
        history = getattr(channel, "history", None)
        if history is None:
            return None

        async for message in history(
            after=period.start,
            before=period.end,
            oldest_first=True,
            limit=None,
        ):
            text = (message.content or "").strip()
            if not text:
                continue
            messages.append(
                RawMessage(
                    ts=f"{message.created_at.timestamp():.6f}",
                    author=self._author_name(message.author),
                    text=text,
                )
            )

        if not messages:
            return None

        return RawConversation(
            id=str(getattr(channel, "id", title)),
            title=title,
            kind=kind,
            messages=tuple(messages),
        )

    @staticmethod
    def _author_name(author: object) -> str:
        name = getattr(author, "display_name", None) or getattr(author, "name", None)
        return str(name or getattr(author, "id", "unknown"))

    @staticmethod
    def _title(channel: object, kind: str) -> str:
        if kind == "guild_text":
            return f"#{getattr(channel, 'name', 'unknown')}"
        if kind == "thread":
            parent = getattr(channel, "parent", None)
            parent_name = getattr(parent, "name", "unknown")
            thread_name = getattr(channel, "name", "thread")
            return f"#{parent_name} / 🧵 {thread_name}"
        if kind == "dm":
            recipient = getattr(channel, "recipient", None)
            recipient_name = getattr(recipient, "name", None) or "unknown"
            return f"@{recipient_name}"
        if kind == "group_dm":
            group_name = getattr(channel, "name", None) or "group-dm"
            return f"Group DM: {group_name}"
        return getattr(channel, "name", "conversation")


def _intents() -> "discord.Intents":
    """Build intents required for read-only conversation collection."""
    intents = discord.Intents.none()
    intents.guilds = True
    intents.messages = True
    intents.dm_messages = True
    intents.message_content = True
    return intents
