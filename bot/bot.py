# bot_main.py
# IMPORT
import glob
import logging
from datetime import datetime
from typing import MappingProxyType, Optional

import asyncpg
import discord
from discord.ext import commands


class Config(dict):
    """
    Similar to a dict, this is the configuration of the application
    """

    def __init__(self, defaults: Optional[dict] = None):
        super().__init__(defaults or {})

    def from_object(self, obj: object) -> None:
        """
        Loads a configuration from an object, will only load upper case
        attributes of the class and set them as keys to this object.

        :param obj: an object
        """
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)


class Bot(commands.Bot):

    # Default configuration parameters.
    default_config = MappingProxyType(
        {
            "DEBUG": False,
            "DB_NAME": "discord",
            "DB_USER": "discord",
            "DB_PASSWORD": "discord",
            "DB_HOST": "127.0.0.1",
            "DB_ENABLED": True,
        }
    )

    def __init__(self, config=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Configure logger
        logger = logging.getLogger("discord").setLevel(logging.DEBUG)
        logging.getLogger("discord.http").setLevel(logging.INFO)
        logger = logging.getLogger("discord_bot")
        logger.propagate = False
        logger.setLevel(logging.DEBUG)

        log_formatter = logging.Formatter(
            fmt="%(asctime)s - %(filename)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        # File-logs
        file_handler = logging.FileHandler(filename="bot.log", encoding="utf-8", mode="w")
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)

        # Console-logs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)

        self.log = logger

        self.config: Config = Config(defaults=self.default_config)
        if config is not None:
            self.config.from_object(config)

        self.db = None

        self.uptime = datetime.now()

    async def on_ready(self) -> None:
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.listening, name=f"{self.command_prefix} help"),
        )

        self.log.info(msg=f"Logged as: {self.user} | Guilds: {len(self.guilds)} Users: {len(self.users)}")
        for guild in self.guilds:
            self.log.info(msg=f"{self.user} connected to: {guild.name} (id: {guild.id})")

    async def startup(self) -> None:
        """Sync application commands"""
        await self.wait_until_ready()

        await self.tree.sync()

    async def close(self) -> None:
        self.log.info(msg="Shutting Down")
        if self.db is not None:
            await self.db.close()
            self.log.info(msg="Database connection closed")
        await super().close()

    async def setup_hook(self) -> None:
        """Initialize the db, prefixes & cogs."""

        # Database initialization
        credentials = {
            "database": self.config["DB_NAME"],
            "user": self.config["DB_USER"],
            "password": self.config["DB_PASSWORD"],
            "host": self.config["DB_HOST"],
        }
        try:
            self.db = await asyncpg.create_pool(**credentials)
            self.log.info(msg="Database connection created")
        except Exception as e:
            self.db = None
            self.log.info(msg=f"Database connection failed: {e}")

        # Cogs loader
        for cog in (f"{filename.replace('/','.')[:-3]}" for filename in glob.glob("cogs/*.py")):
            await self.load_extension(cog)

        # Sync application commands
        self.loop.create_task(self.startup())

    async def on_command(self, ctx: commands.Context):
        self.log.info(f"{ctx.author} ({ctx.author.nick}) used command  {ctx.message.content}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        command = ctx.command
        msg = None

        if isinstance(error, commands.CommandNotFound):
            msg = "Invalid command used."
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            msg = "Insufficent permission."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f"Command is missing the required arguments.:\n{self.command_prefix}{command.qualified_name} {command.signature}"
        else:
            msg = f"An error occured:\n{error}"
            self.log.error(f"Command {command.qualified_name} caused an exception\n{error.original}")

        ctx.reply(msg, delete_after=60)

    async def cogs_manager(self, mode: str, cogs: list[str]) -> None:
        for cog in cogs:
            if mode == "reload":
                await self.reload_extension(cog)
            elif mode == "unload":
                await self.unload_extension(cog)
            elif mode == "load":
                await self.load_extension(cog)
            else:
                raise TypeError(f"Invalid operating mode: {mode}.")

    async def on_error(self, event: str, *args, **kwargs):
        self.log.exception("Event %r caused an exception", event)
