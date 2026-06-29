"""Thin, paginated wrapper around the Slack Web API.

Uses a Slack *user* OAuth token (``xoxp-``) so the tool sees every
conversation the user can see. Cursor pagination and rate-limit/connection
retries are handled here so callers can iterate results without ceremony.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.http_retry.builtin_handlers import (
    ConnectionErrorRetryHandler,
    RateLimitErrorRetryHandler,
)

from ..errors import SlackCollectionError

_PAGE_SIZE = 200
_CONVERSATION_TYPES = "public_channel,private_channel,mpim,im"


class SlackClient:
    """Paginated, retry-aware Slack Web API client."""

    def __init__(self, token: str) -> None:
        self._client = WebClient(
            token=token,
            retry_handlers=[
                RateLimitErrorRetryHandler(max_retry_count=5),
                ConnectionErrorRetryHandler(max_retry_count=3),
            ],
        )

    def _paginate(
        self,
        method: Callable[..., Any],
        *,
        result_key: str,
        **params: Any,
    ) -> Iterator[dict[str, Any]]:
        """Yield every item across all cursor-paginated pages of ``method``."""
        cursor: str | None = None
        while True:
            call_params = dict(params, limit=_PAGE_SIZE)
            if cursor:
                call_params["cursor"] = cursor
            try:
                response = method(**call_params)
            except SlackApiError as err:
                raise SlackCollectionError(
                    f"Slack API call '{method.__name__}' failed: "
                    f"{err.response.get('error', err)}"
                ) from err

            yield from response.get(result_key, [])
            cursor = (response.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break

    def users(self) -> Iterator[dict[str, Any]]:
        """Iterate every workspace user record."""
        return self._paginate(self._client.users_list, result_key="members")

    def conversations(self) -> Iterator[dict[str, Any]]:
        """Iterate all non-archived conversations visible to the user."""
        return self._paginate(
            self._client.conversations_list,
            result_key="channels",
            types=_CONVERSATION_TYPES,
            exclude_archived=True,
        )

    def history(
        self, channel_id: str, oldest: str, latest: str
    ) -> Iterator[dict[str, Any]]:
        """Iterate top-level messages of a conversation within a window."""
        return self._paginate(
            self._client.conversations_history,
            result_key="messages",
            channel=channel_id,
            oldest=oldest,
            latest=latest,
            inclusive=True,
        )

    def replies(
        self, channel_id: str, thread_ts: str, oldest: str, latest: str
    ) -> Iterator[dict[str, Any]]:
        """Iterate the messages of a single thread within a window."""
        return self._paginate(
            self._client.conversations_replies,
            result_key="messages",
            channel=channel_id,
            ts=thread_ts,
            oldest=oldest,
            latest=latest,
            inclusive=True,
        )
