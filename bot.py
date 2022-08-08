# bot_main.py
### IMPORT ###
import discord
from discord.ext import commands

from roles import admin_roles, elevated_roles

import os
import logging
import asyncio
import asyncpg
from datetime import datetime
from dotenv import load_dotenv

### TOKENS ###
# load the env files
load_dotenv('.env')
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
DB_PSWD = os.getenv("DB_PSWD")

# check token
if BOT_TOKEN == None:
    print('Invalid .env Token')
    exit()

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # logger = logging.getLogger("discord") # discord.py logger
        logger = logging.getLogger("discord_bot") # discord.py logger
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        log_formatter = logging.Formatter(fmt='%(asctime)s - %(filename)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
        # File-logs
        file_handler = logging.FileHandler(filename='bot.log', encoding="utf-8", mode='w')
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        # Console-logs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

        self.logger = logger
        self.db = None

        self.uptime = datetime.now()

    async def on_ready(self):
        await client.change_presence(status=discord.Status.online,
                activity=discord.Activity(type=discord.ActivityType.listening, name=f'{self.command_prefix} help'))

        self.logger.info(msg=f"Logged as: {self.user} | Guilds: {len(self.guilds)} Users: {len(self.users)}")
        for guild in self.guilds:
            self.logger.info(msg=f'{self.user} connected to: {guild.name} (id: {guild.id})')

    async def startup(self):
        """Sync application commands"""
        await self.wait_until_ready()

        await self.tree.sync()

    async def close(self):
        if self.db is not None:
            await self.db.close()
            self.logger.info(msg="Database connection closed")
        await super().close()


    async def setup_hook(self):
        """Initialize the db, prefixes & cogs."""

		#Database initialization
        credentials = {
            "user": "pi",
            "password": DB_PSWD,
            "database": "discord",
            "host": "127.0.0.1"}
        try:
            self.db = await asyncpg.create_pool(**credentials)
            self.logger.info(msg="Database connection created")
        except Exception as e:
            self.db = None
            self.logger.info(msg=f"Database connection failed: {e}")

        # Cogs loader
        cogs = [f"cogs.{filename[:-3]}" for filename in os.listdir("./cogs") if filename.endswith(".py")]
        await self.cogs_manager("load", cogs)

        # Sync application commands
        self.loop.create_task(self.startup())

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply('Invalid command used.', delete_after=15)
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.reply('Insufficent permission.', delete_after=15)
        elif isinstance(error,commands.MissingRequiredArgument):
            await ctx.reply('Command is missing the required arguments.', delete_after=15)
        elif isinstance(error, commands.ExtensionNotLoaded):
            await ctx.reply('Extension has not been loaded.', delete_after=15)
        else:
            await ctx.reply(f'An error occured:\n{error}', delete_after=120)
            self.logger.info(f'An error occured: {error}')



    async def cogs_manager(self, mode: str, cogs: list[str]) -> None:
        for cog in cogs:
            try:
                if mode == "reload":
                    await self.reload_extension(cog)
                elif mode == "unload":
                    await self.unload_extension(cog)
                elif mode == "load":
                    await self.load_extension(cog)
                else:
                    raise TypeError(f"Invalid operating mode: {mode}.")
            except Exception as e:
                raise e


### CLIENT ###

client = Bot(
    command_prefix='.cs ',
    intents=discord.Intents.all(),
    allowed_mentions=discord.AllowedMentions(everyone=False),
    case_insensitive = True
)

async def main():
    async with client:
        await client.start(BOT_TOKEN)

# run
asyncio.run(main())
