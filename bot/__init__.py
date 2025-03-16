import logging
import os
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import discord
from discord import app_commands
from discord.ext import commands, tasks
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Session, dbconfig, engine
import aiohttp


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        """
        Create a new Discord bot.
        Any additional args and kwargs are passed to discord.commands.Bot.

        :param config: Bot Configuration object, defaults to None
        """
        super().__init__(*args, **kwargs)

        self.uptime = datetime.now(timezone.utc)

        self.load_enviroment()
        self.configure_logging()
        self.init_database()

    def load_enviroment(self) -> None:
        """
        Load defaults or settings enviroment variables
        """

        class Config:
            debug = os.getenv("DEBUG", False)
            logfile_location = os.getenv("LOGFILE_LOCATION", os.getcwd() + "/logs")
            logging_enabled = os.getenv("LOGGING_ENABLED", True)

        self.config = Config()
        self.dbconfig = dbconfig
        self.modules = {}

        # configure Heatbeat
        heartbeat = os.getenv("HEARTBEAT_DESTINATION", False)
        if heartbeat:
            self._heartbeat = heartbeat
            self.heartbeat.start()
        else:
            self._heartbeat = None

    @tasks.loop(seconds=int(os.getenv("HEARTBEAT_INTERVAL", 60)))
    async def heartbeat(self):
        """
        Send a heartbeat to the configured destination
        """
        method = os.getenv("HEARTBEAT_METHOD", "GET")
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(self._heartbeat) as response:
                    status_code = response.status
            elif method == "POST":
                async with session.post(self._heartbeat) as response:
                    status_code = response.status
            else:
                self.log.error(f"Invalid heartbeat method: {method}")
                return
            if status_code != 200:
                self.log.error(f"Failed to send heartbeat ({self._heartbeat}): {status_code}")
            else:
                self.log.debug(f"Sent heartbeat ({self._heartbeat})")

    def configure_logging(self) -> None:
        """
        Setup log files and levels
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

    async def load_cogs(self) -> None:
        """
        Load default configuration cogs and any additional cogs specified in the COGS environment variable.
        """
        # Load any default cogs
        default_cogs = ["cogs.setup", "cogs.administrative", "cogs.general"]
        extra = os.getenv("COGS", "").split(",")
        default_cogs.extend([f"cogs.{cog}" for cog in extra if cog])
        for cog in default_cogs:
            self.log.info(msg=f"Loading: {cog}")
            try:
                await self.load_extension(cog)
            except commands.ExtensionNotFound:
                self.log.error(f"Extension '{cog}' does not exist")
            except commands.ExtensionAlreadyLoaded:
                self.log.error(f"Extension '{cog}' is already loaded")
            except (commands.NoEntryPointError, commands.ExtensionFailed):
                self.log.error(f"Extension '{cog}' failed to load")
            except Exception as e:
                self.log.error(f"An unexpected error occurred while loading '{cog}': {e}")

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
        # NOTE: We are loading cogs here and not in setup_hook because some cogs may require guild data
        await self.load_cogs()

    async def close(self) -> None:
        """
        Closes the connection to Discord and the database.
        """
        if self.db is not None:
            await self.db.dispose()
            self.log.info(msg="Database connection closed")

        if self._heartbeat:
            self.heartbeat.cancel()

        self.log.info("Shutting Down")
        await super().close()

    async def setup_hook(self) -> None:
        """Initialize the setup data."""
        pass

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
        if interaction.command:
            interaction_name = interaction.command.qualified_name
        elif interaction.message and interaction.message.interaction:
            interaction_name = f"Component from {interaction.message.interaction.name}"
        else:
            interaction_name = "Component"
        user = interaction.user
        if isinstance(user, discord.Member):
            user_id = f"{user} ({user.nick})"
        elif isinstance(user, discord.User):
            user_id = user.name
        else:
            user_id = user
        guild = interaction.guild
        if guild:
            guild_id = f"{guild} ({guild.id})"
        else:
            guild_id = "DM"
            
        self.log.info(f"{interaction_name} interaction by user {user_id} requested on {guild_id}")

    async def on_app_command_completion(self, interaction: discord.Interaction, _):
        user = interaction.user
        if isinstance(user, discord.Member):
            user_id = f"{user} ({user.nick})"
        elif isinstance(user, discord.User):
            user_id = user.name
        else:
            user_id = user
        guild = interaction.guild
        if guild:
            guild_id = f"{guild} ({guild.id})"
        else:
            guild_id = "DM"
        self.log.info(
            f"{interaction.command.qualified_name} interaction by user {user_id} completed on {guild_id}"
        )

    def error_message(
        self, command: commands.Command, error: commands.CommandError | app_commands.errors.AppCommandError
    ) -> discord.Embed:
        """
        Generate an error message

        :param command: command that caused the error
        :param error: error to generate message for
        :return: error message
        """
        if isinstance(error, (commands.BotMissingPermissions, app_commands.errors.BotMissingPermissions)):
            msg = "Bot does not have sufficient permissions."
        if isinstance(error, (commands.CommandNotFound, app_commands.errors.CommandNotFound)):
            msg = "Invalid command used."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f"Command is missing the required arguments.:\n{self.command_prefix}{command.qualified_name} {command.signature}"
        elif isinstance(error, app_commands.errors.CommandOnCooldown):
            msg = f'Command "{command.name}" is on cooldown, you can use it in {round(error.retry_after, 2)} seconds.'
        elif isinstance(error, (commands.MissingPermissions, app_commands.errors.MissingPermissions)):
            msg = "You do not have sufficient permissions."
        else:
            msg = f"An error occured:\n{error}"
            # add stack trace if in debug mode
            if self.config.debug:
                msg += f"\n```{traceback.format_exc()}```"
            self.log.error(f"Command {command.qualified_name} caused an exception: {error}")
        embed = discord.Embed(
            title=f"**__Error__**",
            description=msg[:4096],  # Discord message limit
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
            await ctx.message.add_reaction("\u274c")
        except discord.errors.NotFound:
            pass
        await ctx.reply(embed=self.error_message(command, error), delete_after=60)

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
