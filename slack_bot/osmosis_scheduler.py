"""
Osmosis Scheduler

Runs alongside the Slack bot. Every N minutes, checks for due goals
and sends check-in messages via Slack.
"""

import asyncio
import logging
from typing import Dict

from core.osmosis import get_due_check_ins, process_check_in_response

logger = logging.getLogger("openpriors.osmosis.scheduler")

# Track which check-ins are awaiting responses: {thread_ts: goal_id}
_pending_responses: Dict[str, str] = {}

CHECK_INTERVAL_SECONDS = 300  # check every 5 minutes


async def run_check_ins(client):
    """Check for due goals and send messages."""
    due = await get_due_check_ins()
    if not due:
        return

    logger.info(f"Sending {len(due)} check-in(s)")

    for check_in in due:
        channel = check_in.get("slack_channel")
        if not channel:
            logger.warning(f"Goal {check_in['goal_id']} has no slack_channel, skipping")
            continue

        try:
            result = await client.chat_postMessage(
                channel=channel,
                text=check_in["message"],
            )
            # Track the thread so we can match the user's response
            ts = result.get("ts", "")
            if ts:
                _pending_responses[ts] = check_in["goal_id"]
                logger.info(f"Check-in sent for goal {check_in['goal_id']} in {channel}")
        except Exception as e:
            logger.error(f"Failed to send check-in: {e}")


async def handle_check_in_reply(event, client):
    """Handle a user's reply to a check-in message."""
    thread_ts = event.get("thread_ts")
    if not thread_ts or thread_ts not in _pending_responses:
        return False

    goal_id = _pending_responses.pop(thread_ts)
    user_response = event.get("text", "")

    try:
        follow_up = await process_check_in_response(goal_id, user_response)
        await client.chat_postMessage(
            channel=event["channel"],
            thread_ts=thread_ts,
            text=follow_up,
        )
        # Add checkmark
        await client.reactions_add(
            channel=event["channel"],
            name="white_check_mark",
            timestamp=event["ts"],
        )
    except Exception as e:
        logger.error(f"Failed to process check-in reply: {e}")

    return True


async def scheduler_loop(client):
    """Background loop that checks for due goals every N seconds."""
    logger.info(f"Osmosis scheduler started (checking every {CHECK_INTERVAL_SECONDS}s)")
    while True:
        try:
            await run_check_ins(client)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
