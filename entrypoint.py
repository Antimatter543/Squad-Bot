import asyncio
import sys
from os import getenv

from bot import get_bot

# Get & Validate Discord Bot Token

if (BOT_TOKEN := getenv("BOT_TOKEN")) is None:
    print("No Valid Discord BOT Token found in environment")
    print("Is the BOT_TOKEN environment variable set?")
    sys.exit(1)

# Start Bot Client
async def main():
    bot = get_bot()
    async with bot:
        await bot.start(BOT_TOKEN)


# run
asyncio.run(main())