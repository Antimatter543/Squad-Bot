import glob
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import asyncpg
import discord
from discord.ext import commands

from bot.settings import Settings


class Config(dict):
    """
    Similar to a dict, this is the configuration of the application
    """

    def __init__(self, defaults: Optional[dict[str, bool | str]] = None):
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
    default_config: dict[str, str | bool] = {
        "DEBUG": False,
        "DB_NAME": "discord",
        "DB_USER": "discord",
        "DB_PASSWORD": "discord",
        "DB_HOST": "127.0.0.1",
        "DB_PORT": "5432",
        "DB_ENABLED": True,
    }

    def __init__(self, config=None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Configure logger
        logger = logging.getLogger("discord").setLevel(logging.INFO)
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

        self.config: Config = Config(defaults=dict(self.default_config))
        if config is not None:
            self.config.from_object(config)

        self.settings: Settings = Settings(self)

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

    async def close(self) -> None:
        if self.db is not None:
            await self.db.close()
            self.log.info(msg="Database connection closed")

        self.log.info(msg="Shutting Down")
        await super().close()

    async def setup_hook(self) -> None:
        """Initialize the db, prefixes & cogs."""

        # Database initialization
        credentials = {
            "database": self.config["DB_NAME"],
            "user": self.config["DB_USER"],
            "password": self.config["DB_PASSWORD"],
            "host": self.config["DB_HOST"],
            "port": self.config["DB_PORT"],
        }
        try:
            self.db = await asyncpg.create_pool(**credentials)
            self.log.info(msg="Database connection created")
        except Exception as e:
            self.db = None
            msg = f"Database connection failed: {e}"
            self.log.info(msg)
            print(msg, file=sys.stderr)
            await self.close()
            sys.exit(1)

        await self.settings.load_settings()
        # Cogs loader
        # navigate to this files folder
        cdir = os.getcwd()
        os.chdir(os.path.dirname(__file__))
        sys.path.insert(0, os.getcwd())
        for cog in (f"{filename.replace('/','.')[:-3]}" for filename in glob.glob("cogs/**/*.py", recursive=True)):
            self.log.info(msg=f"Loading: {cog}")
            await self.load_extension(cog)
        # restore old directory in case user is expecting
        os.chdir(cdir)

    async def on_command(self, ctx: commands.Context):
        self.log.info(f"{ctx.author} ({ctx.author.nick}) used command  {ctx.message.content}")

    async def on_interaction(self, interaction: discord.Interaction):
        self.log.info(f"{interaction.user} ({interaction.user.nick}) used command  {interaction.message.content}")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        command: commands.Command = ctx.command
        msg = None
        try:
            await ctx.message.add_reaction("\u274C")
        except discord.errors.NotFound:
            pass
        if isinstance(error, commands.BotMissingPermissions):
            msg = "Bot does not have sufficient permissions."
        if isinstance(error, commands.CommandNotFound):
            msg = "Invalid command used."
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            msg = "Insufficent permission."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f"Command is missing the required arguments.:\n{self.command_prefix}{command.qualified_name} {command.signature}"
        else:
            msg = f"An error occured:\n{error}"
            self.log.error(f"Command {command.qualified_name} caused an exception: {error}")
        aEmbed = discord.Embed(
            title=f"**__Error__**",
            description=msg,
            colour=discord.Colour.red(),
        )
        await ctx.reply(embed=aEmbed, delete_after=60)

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
