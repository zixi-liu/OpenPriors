"""Slack event handlers — link detection, extraction, thread reply, osmosis check-ins."""

import re
import logging
from slack_bolt.async_app import AsyncApp

from core.pipeline import process_url
from core.storage import create_goal, get_prior
from slack_bot.formatter import format_extraction_blocks, format_fallback_text
from slack_bot.osmosis_scheduler import handle_check_in_reply

logger = logging.getLogger("openpriors.slack")

URL_PATTERN = re.compile(r'https?://[^\s>|]+')
GOAL_PATTERN = re.compile(r'^/goal\s+(.+)', re.IGNORECASE)

# Track processed messages to avoid duplicates
_processed: set = set()


def register_handlers(app: AsyncApp):

    @app.event("message")
    async def handle_message(event, client):
        # Skip bot messages and edits
        if event.get("bot_id") or event.get("subtype"):
            return

        msg_key = (event.get("channel"), event.get("ts"))
        if msg_key in _processed:
            return
        _processed.add(msg_key)

        # Cap memory
        if len(_processed) > 500:
            for k in list(_processed)[:250]:
                _processed.discard(k)

        text = event.get("text", "")
        channel = event["channel"]

        # --- Check if this is a reply to an osmosis check-in ---
        handled = await handle_check_in_reply(event, client)
        if handled:
            return

        # --- /goal command: create a goal from a prior ---
        goal_match = GOAL_PATTERN.match(text)
        if goal_match:
            await _handle_goal_command(goal_match.group(1).strip(), channel, event, client)
            return

        # --- Link detection: extract priors ---
        urls = URL_PATTERN.findall(text)
        if not urls:
            return

        thread_ts = event.get("thread_ts") or event["ts"]

        try:
            await client.reactions_add(
                channel=channel,
                name="hourglass_flowing_sand",
                timestamp=event["ts"],
            )
        except Exception:
            pass

        for url in urls:
            try:
                result = await process_url(url)

                if not result.get("success"):
                    await client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text=f"Couldn't extract content from {url}",
                    )
                    continue

                blocks = format_extraction_blocks(result)
                fallback = format_fallback_text(result)

                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    blocks=blocks,
                    text=fallback,
                )

                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="What would you like to do with these insights? I can help you set goals, create a practice plan, or explore deeper.\n\nTip: Use `/goal <description>` to start tracking a habit.",
                )

            except Exception as e:
                logger.exception(f"Error processing {url}")
                await client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text="Something went wrong processing that link. Try again later.",
                )

        try:
            await client.reactions_remove(
                channel=channel,
                name="hourglass_flowing_sand",
                timestamp=event["ts"],
            )
            await client.reactions_add(
                channel=channel,
                name="white_check_mark",
                timestamp=event["ts"],
            )
        except Exception:
            pass


async def _handle_goal_command(description: str, channel: str, event: dict, client):
    """Handle /goal <description> — create a goal and start tracking."""
    thread_ts = event.get("thread_ts") or event["ts"]

    goal_id = create_goal(
        description=description,
        cadence="daily",
        slack_channel=channel,
    )

    await client.chat_postMessage(
        channel=channel,
        thread_ts=thread_ts,
        text=f"Goal set: *{description}*\n\nI'll check in with you daily to see how it's going. You can change the cadence anytime.",
    )

    await client.reactions_add(
        channel=channel,
        name="dart",
        timestamp=event["ts"],
    )
