import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Session, dbconfig, engine


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        """
        Create a new Discord bot.
        Any additional args and kwargs are passed to discord.commands.Bot.

        :param config: Bot Configuration object, defaults to None
        """
        super().__init__(*args, **kwargs)

        self.uptime = datetime.utcnow()

        self.load_enviroment()
        self.configure_logging()
        self.init_database()

    def load_enviroment(self) -> None:
        """
        Load defaults or settings enviroment variables
        """

        class Config:
            debug = os.getenv("DEBUG", False)
            logfile_location = os.getenv("LOGFILE_LOCATION", os.getcwd())
            logging_enabled = os.getenv("LOGGING_ENABLED", True)

        self.config = Config()
        self.dbconfig = dbconfig
        self.modules = {}

    def configure_logging(self) -> None:
        """
        Configure logging
        """
        if not self.config.logging_enabled:
            return

        # Configure default discord logger
        logger = logging.getLogger("discord")
        logger.setLevel(logging.INFO)
        handler = RotatingFileHandler(
            filename=f"{self.config.logfile_location}/discord.log",
            encoding="utf-8",
            maxBytes=64 * 1024 * 1024,  # 64 MiB
            backupCount=3,  # Rotate through 3 files
        )
        logger.addHandler(handler)

        logging.getLogger("discord.http").setLevel(logging.INFO)

        # Configure our logger
        log_level = logging.DEBUG if self.config.debug else logging.INFO
        self.log = logging.getLogger("bot")
        self.log.setLevel(log_level)
        self.log.propagate = False
        log_formatter = logging.Formatter(
            fmt="%(asctime)s - %(filename)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        # File Logs
        file_handler = RotatingFileHandler(
            filename=f"{self.config.logfile_location}/bot.log",
            encoding="utf-8",
            maxBytes=64 * 1024 * 1024,  # 64 MiB
            backupCount=3,  # Rotate through 3 files
        )
        file_handler.setFormatter(log_formatter)
        self.log.addHandler(file_handler)

        # Console Logs
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
        self.log.addHandler(console_handler)

    def init_database(self) -> None:
        """
        Assign the database engine to the bot.
        """
        self.db = None
        if not self.dbconfig.enabled:
            return
        self.db = engine

    @property
    def session(self) -> AsyncSession:
        """
        Get the current database session.

        :return: The current database session.
        """
        if not self.dbconfig.enabled:
            raise Exception("Database functionality is not enabled")
        return Session()

    async def on_ready(self) -> None:
        """
        Called when the client is done preparing the data received from Discord.
        Set's up the status and logs which guilds are currently connected.
        """
        await self.wait_until_ready()
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(type=discord.ActivityType.listening, name=f"{self.command_prefix} help"),
        )
        self.log.info(f"Logged in as {self.user} ({self.user.id}) | # Guilds: {len(self.guilds)}")

    async def close(self) -> None:
        """
        Closes the connection to Discord and the database.
        """
        if self.db is not None:
            await self.db.dispose()
            self.log.info(msg="Database connection closed")

        self.log.info("Shutting Down")
        await super().close()

    async def setup_hook(self) -> None:
        """Initialize the db, prefixes & cogs."""

        # Cogs loader
        # Load any default cogs
        default_cogs = ["cogs.setup", "cogs.administrative", "cogs.general"]
        for cog in default_cogs:
            self.log.info(msg=f"Loading: {cog}")
            await self.load_extension(cog)

    async def on_command(self, ctx: commands.Context):
        """
        Log commands that are run

        :param ctx: context of the command
        """
        author = ctx.author
        if isinstance(author, discord.abc.User):
            nick = "N/A"
        elif isinstance(author, discord.Member):
            nick = author.nick
        else:
            nick = None
        command = ctx.command
        if command is None:
            command = ctx.message.content

        self.log.info(f"{author} ({nick}) used command: {command}")

    async def on_interaction(self, interaction: discord.Interaction):
        """
        Log interactions

        :param interaction: interaction to log
        """
        author = interaction.user
        if isinstance(author, discord.abc.User):
            nick = "N/A"
        elif isinstance(author, discord.Member):
            nick = author.nick
        else:
            nick = None
        command = interaction.command
        if command is None and interaction.message is not None:
            command = interaction.message.content
        else:
            command = "Unkown"
        self.log.info(f"{author} ({nick}) used command  {command}")

    def error_message(
        self, command: commands.Command, error: commands.CommandError | app_commands.errors.AppCommandError
    ) -> discord.Embed:
        """
        Generate an error message

        :param command: command that caused the error
        :param error: error to generate message for
        :return: error message
        """
        if isinstance(error, commands.BotMissingPermissions) or isinstance(
            error, app_commands.errors.BotMissingPermissions
        ):
            msg = "Bot does not have sufficient permissions."
        if isinstance(error, commands.CommandNotFound) or isinstance(error, app_commands.errors.CommandNotFound):
            msg = "Invalid command used."
        elif isinstance(error, commands.CommandInvokeError) and isinstance(
            error, app_commands.errors.CommandInvokeError
        ):
            msg = "Insufficent permission."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f"Command is missing the required arguments.:\n{self.command_prefix}{command.qualified_name} {command.signature}"
        elif isinstance(error, app_commands.errors.CommandOnCooldown):
            msg = f'Command "{command.name}" is on cooldown, you can use it in {round(error.retry_after, 2)} seconds.'

        else:
            msg = f"An error occured:\n{error}"
            self.log.error(f"Command {command.qualified_name} caused an exception: {error}")
        embed = discord.Embed(
            title=f"**__Error__**",
            description=msg,
            colour=discord.Colour.red(),
        )
        return embed

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """
        Send feedback to user on error

        :param ctx: command context
        :param error: error context
        """
        command = ctx.command
        if command is None:
            return
        try:
            await ctx.message.add_reaction("\u274C")
        except discord.errors.NotFound:
            pass
        await ctx.reply(embed=self.error_message(command, error), delete_after=60)

    async def cogs_manager(self, mode: str, cogs: list[str]) -> None:
        """
        Single function to manage extentions

        :param mode: cog interaction
        :param cogs: cog(s) to operate on
        :raises TypeError: if mods is not in ["reload", "unload", "load"]
        """
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


def get_bot() -> Bot:
    """
    Get the bot instance

    :return: bot instance
    """

    bot = Bot(
        command_prefix=os.getenv("BOT_PREFIX", ".tt "),
        intents=discord.Intents.all(),
        allowed_mentions=discord.AllowedMentions(everyone=False),
        case_insensitive=True,
    )

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if interaction.response.is_done():
            cmd = interaction.followup.send
        else:
            cmd = interaction.response.send_message
        await cmd(embed=bot.error_message(interaction.command, error), ephemeral=True)

    return bot
