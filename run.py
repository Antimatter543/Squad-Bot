import asyncio
import sys
from os import getenv

from bot import get_bot

# Get & Validate Discord Bot Token

if (BOT_TOKEN := getenv("BOT_TOKEN")) is None:
    print("Invalid .env Token")
    sys.exit(1)

# Start Bot Client


async def main():
    bot = get_bot()
    async with bot:
        await bot.start(BOT_TOKEN)


# run
asyncio.run(main())
