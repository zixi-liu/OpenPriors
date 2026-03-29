"""
OpenPriors Slack Bot

Run: python -m slack_bot.bot

Features:
  - Paste a link → extracts priors, saves everything, replies in-thread
  - /goal <description> → creates a goal, osmosis agent checks in on schedule
  - Osmosis agent runs in background, sends check-ins for due goals
"""

import asyncio
import logging
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from slack_bot.config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN, validate
from slack_bot.handlers import register_handlers
from slack_bot.osmosis_scheduler import scheduler_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger("openpriors.slack")


async def main():
    validate()
    app = AsyncApp(token=SLACK_BOT_TOKEN)
    register_handlers(app)

    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

    logger.info("OpenPriors Slack bot starting (Socket Mode)...")
    logger.info("Osmosis scheduler starting...")

    # Run Socket Mode + osmosis scheduler concurrently
    await asyncio.gather(
        handler.start_async(),
        scheduler_loop(app.client),
    )


if __name__ == "__main__":
    asyncio.run(main())
