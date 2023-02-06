# Example discord bot initialisation
import asyncio
from os import getenv

import discord

# requires python-dotenv
from dotenv import load_dotenv

from bot import Bot

# TOKENS
# load the env files
load_dotenv(".env")
BOT_TOKEN = getenv("DISCORD_TOKEN")

# check token
if BOT_TOKEN is None:
    print("Invalid .env Token")
    exit()


class Config(object):
    DB_NAME = "discord"
    DB_USER = "discord"
    DB_PASSWORD = getenv("DB_PASSWORD")
    DB_HOST = "127.0.0.1"


# CLIENT

client = Bot(
    config=Config(),
    command_prefix="..p ",
    intents=discord.Intents.all(),
    allowed_mentions=discord.AllowedMentions(everyone=False),
    case_insensitive=True,
)


async def main():
    async with client:
        await client.start(BOT_TOKEN)


# run
asyncio.run(main())
