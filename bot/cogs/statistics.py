import re
from datetime import datetime, timedelta
from random import randint
from typing import Optional

import discord
import pytz
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select

from bot.database.models import Screams, StatisticsConfig
from bot.lib import DefaultDiscordObject
from bot.lib.date import epoch, now_tz

cog_name = "statistics"


class statistics(commands.Cog):
    class Config:
        def __init__(self) -> None:
            self.regexp_primary = re.compile(r"[aA][arRgGAhH]{" + re.escape(str(randint(5, 15))) + r",}")
            self.regexp_secondary = re.compile(r":scream1:")
            self.channel = DefaultDiscordObject()
            self.minor_threshold = 100
            self.major_threshold = 250
            self.minor_role = DefaultDiscordObject()
            self.major_role = DefaultDiscordObject()

        @classmethod
        async def from_row(cls, bot: commands.Bot, row: StatisticsConfig):
            """
            Create a new Config object from a row in the database

            :param commands.Bot bot: the bot instance
            :param StatisticsConfig row: the stored DB config
            :raises ValueError: if the row is None
            """
            if row is None:
                raise ValueError("Could not find a row in the database for this guild.")
            obj = cls()
            try:
                guild: discord.Guild | None = await bot.fetch_guild(row.guild_id)
                if guild is None:
                    return obj
                try:
                    channel = await guild.fetch_channel(row.channel_id)
                    obj.channel = channel
                except discord.errors.NotFound:
                    pass
                if (minor_role := guild.get_role(row.minor_role_id)) is not None:
                    obj.minor_role = minor_role
                if (major_role := guild.get_role(row.major_role_id)) is not None:
                    obj.major_role = major_role
            except discord.Forbidden:
                bot.log.warning(f"Could not find a channel or role for guild {row.guild_id}")
                pass
            try:
                if row.regexp_primary is not None:
                    obj.regexp_primary = re.compile(row.regexp_primary)
                if row.regexp_secondary is not None:
                    obj.regexp_secondary = re.compile(row.regexp_secondary)
            except re.error:
                bot.log.warning(f"Could not compile the regex for guild {row.guild_id}")
                pass
            obj.minor_threshold = row.minor_threshold
            obj.major_threshold = row.major_threshold

            return obj

    stats_group = app_commands.Group(name="stats", description="Statistics / Scream commands")

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.log = bot.log
        self.log.info(f"Loaded {self.__class__.__name__}")

        bot.modules[cog_name] = {}
        for guild in bot.guilds:
            bot.modules[cog_name][guild.id] = self.Config()

        self.stats_menu = app_commands.ContextMenu(
            name="statistics",
            callback=self.statistics_menu,
        )
        self.bot.tree.add_command(self.stats_menu)

        self.hasscreamed_menu = app_commands.ContextMenu(
            name="Have they screamed?",
            callback=self.didiscream_menu,
        )
        self.bot.tree.add_command(self.hasscreamed_menu)

    async def _init(self):
        """
        Any initialisation code that needs to be run after the bot is ready or
        in async context.

        :raises Exception: if the database is not enabled
        """
        self.log.info(f"Initialised {self.__class__.__name__}")

        if self.bot.db is None:
            raise Exception("This cog requires a database to be enabled.")

        async with self.bot.db.begin() as conn:
            await conn.run_sync(Screams.__table__.create, checkfirst=True)
            await conn.run_sync(StatisticsConfig.__table__.create, checkfirst=True)

        for guild in self.bot.guilds:
            await self.enroll(guild.id)

    async def enroll(self, guild_id):
        async with self.bot.session as session:
            self.log.info(f"{cog_name} - Enrolling guild {guild_id}")
            row = await session.get(StatisticsConfig, guild_id)
            if row is None:
                return
            self.bot.modules[cog_name][guild_id] = await self.Config.from_row(self.bot, row)

    @property
    def today(self) -> datetime:
        """
        Set the time to the start of the day in UTC

        :return: the start of the day in UTC
        """
        return now_tz().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)

    async def get_screams(self, uid: int) -> Screams | None:
        """
        Retrieve the screams for a user from the database

        :param uid: the user id
        :return Screams | None: The row from the database or None
        """
        async with self.bot.session as session:
            return await session.get(Screams, uid)

    @commands.Cog.listener()
    @app_commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def on_message(self, message: discord.Message):
        """
        Listen for messages in the configured channel and update the statistics

        :param discord.Message message: The message object
        """
        # don't respond to bots
        if message.author.bot:
            return
        # check if the message is in the configured channel
        config = self.bot.modules[cog_name].get(message.guild.id)
        if config is None:
            return
        if message.channel == config.channel:
            msg, author = message.content, message.author
            # match the message against the primary and secondary regex
            try:
                match_primary = config.regexp_primary.search(msg)
                match_secondary = config.regexp_secondary.search(msg)
                if match_primary or match_secondary:
                    async with self.bot.session as session, session.begin():
                        user = await session.get(Screams, author.id)
                        if user is None:
                            user = Screams(
                                user_id=author.id,
                                sc_total=0,
                                sc_streak=0,
                                sc_best_streak=0,
                                sc_daily=epoch(),
                                sc_streak_keeper=epoch(),
                            )
                        user.sc_total += 1

                        today = self.today
                        streak = 0
                        if user.sc_daily < today and match_primary:
                            yesterday = today - timedelta(days=1)
                            if user.sc_daily > yesterday:
                                streak = user.sc_streak

                            streak += 1
                            if streak > user.sc_best_streak:
                                user.sc_best_streak = streak
                            user.sc_streak = streak
                            user.sc_daily = now_tz()

                            await message.channel.send(
                                f"Congrats {author.mention} on your first scream of the day.\nYour current streak is: {streak}."
                            )

                            if streak % 100 == 0:
                                await message.channel.send(
                                    "https://i.guim.co.uk/img/media/8a840f693b91fe67d42555b24c6334e9298f4680/251_1497_2178_1306/master/2178.jpg?width=1200&height=900&quality=85&auto=format&fit=crop&s=9ff658ed0e9b905fa583c592cc2342f5"
                                )
                                await message.channel.send(f"Congrats on reaching {streak}!")

                            if streak == config.minor_threshold and config.minor_role is not None:
                                await author.add_roles(config.minor_role)
                            if streak == config.major_threshold and config.major_role is not None:
                                await author.add_roles(config.major_role)
                        session.add(user)
                        await session.commit()
            except Exception as e:
                self.log.info(e)

    async def get_statistics(self, uid, name, avatar) -> discord.Embed:
        row = await self.get_screams(uid)
        embed = discord.Embed(title="Scream Statistics", description="")
        embed.set_author(name=f"{name}")
        embed.set_thumbnail(url=f"{avatar}")
        if row is not None:
            embed.add_field(name="Total Screams", value=f"{row.sc_total}")
            embed.add_field(name="Scream Streak", value=f"{row.sc_streak}")
            embed.add_field(name="Best Scream Streak", value=f"{row.sc_best_streak}")
        else:
            embed.add_field(name="", value="No screams as of yet.")
        return embed

    async def get_has_screamed(self, uid, prefix="", name="User") -> str:
        row = await self.get_screams(uid)
        if row is None:
            return f"{name} has not done any screaming yet."
        if row.sc_daily < self.today:
            msg = "have not"
        else:
            msg = "have"

        return f"{prefix}{msg} screamed today."

    @app_commands.guild_only()
    async def statistics_menu(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        uid = user.id
        name = user.display_name
        avatar = user.display_avatar
        embed = await self.get_statistics(uid, name, avatar)
        msg = await interaction.followup.send(embed=embed, ephemeral=True, wait=True)
        await msg.delete(delay=120)

    @app_commands.guild_only()
    async def didiscream_menu(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        if user == interaction.user:
            start = "You "
        else:
            start = "They "
        uid = user.id
        msg = await self.get_has_screamed(uid, start, user.display_name)
        msg = await interaction.followup.send(content=msg, ephemeral=True, wait=True)
        await msg.delete(delay=120)

    # Commands ========================================================================================================

    @stats_group.command(name="user", description="Get the scream statistics for a user.")
    @app_commands.guild_only()
    async def user_stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        if user is None:
            user = interaction.user
        uid = user.id
        name = user.display_name
        avatar = user.display_avatar
        embed = await self.get_statistics(uid, name, avatar)
        await interaction.followup.send(embed=embed)

    @stats_group.command(description="Check if this user has screamed yet today")
    @app_commands.guild_only()
    async def didiscream(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer(ephemeral=True)
        if user is None:
            user = interaction.user
            start = "You "
        else:
            start = "They "

        uid = user.id
        msg = await self.get_has_screamed(uid, start)
        await interaction.followup.send(msg, ephemeral=True)

    async def get_user(self, aid):
        class UnknownUser:
            def __init__(self) -> None:
                self.display_name = "[Unknown]"

            def __str__(self) -> str:
                return self.display_name

        try:
            user = await self.bot.fetch_user(aid)
            user = UnknownUser() if user is None else user
        except discord.errors.NotFound:
            user = UnknownUser()
        return user

    @stats_group.command(description="Get the top void screamers in the server.")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        top = 5

        async def build_message(rows):
            """
            Generate the top 5 message from the set of rows returned from the database

            :param _type_ rows: _description_
            :return _type_: _description_
            """

            emoji = {1: ":one:", 2: ":two:", 3: ":three:", 4: ":four:", 5: ":five:"}

            message = ""
            count = 0
            for row in rows:
                user = await self.get_user(row.user_id)
                message += f"{emoji[row.rank]}\u27F6 {user.display_name} with {row.sc_col} screams.\n"
                count += 1
            for i in range(count, top):
                message += f"{emoji[i+1]}\u27F6 This could be you!\n"
            return message

        now = round(datetime.timestamp(now_tz()))
        header = "---{ Scream Leaderboard }---"
        await interaction.response.send_message(f"{header}\nLoading... since <t:{now}:R>", ephemeral=False)

        embed = discord.Embed(title=f"{header}", description=f"The top screamers", color=discord.Color.darker_grey())
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1043839508887634010.webp?size=96&quality=lossless")

        async with self.bot.session as session:
            cols = [Screams.sc_total, Screams.sc_streak, Screams.sc_best_streak]
            subqs = [
                (
                    select(Screams.user_id, col.label("sc_col"), func.rank().over(order_by=col.desc()).label("rank"))
                ).subquery()
                for col in cols
            ]
            stmts = [select(subq).where(subq.c.rank <= top) for subq in subqs]

            bestTotal = await session.execute(stmts[0])

            bestStreak = await session.execute(stmts[1])

            bestStreakHistorical = await session.execute(stmts[2])

        embed.add_field(
            name="__Total Number of times screamed__", value=f"{await build_message(bestTotal)}", inline=False
        )

        embed.add_field(name="__Best active daily streak__", value=f"{await build_message(bestStreak)}", inline=False)

        embed.add_field(
            name="__Best historical daily streak__", value=f"{await build_message(bestStreakHistorical)}", inline=False
        )
        await (await interaction.original_response()).edit(content="", embed=embed)

    @stats_group.command(
        name="savestreak", description="If you missed one day sacrifice 30 days of your previous streak to save it."
    )
    @app_commands.describe(
        confirm="You need to confirm you want to sacrifice some of your streak. 'Check' will show you if you can save your streak."
    )
    @app_commands.choices(
        confirm=[app_commands.Choice(name=str(i), value=i) for i in ["True", "False", "Check"]],
    )
    @app_commands.guild_only()
    async def streak_saver(self, interaction: discord.Interaction, confirm: str = "False"):
        await interaction.response.defer(ephemeral=True)
        if confirm == "False":
            await interaction.followup.send(
                "You need to confirm that you want to save your streak by explicitly setting the value to true.",
                ephemeral=True,
            )
            return
        user = interaction.user
        row = await self.get_screams(user.id)
        if row is None:
            await interaction.followup.send(
                f"{user.display_name} has no stats to save.",
                ephemeral=True,
            )
            return
        today = self.today
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        six_months_ago = today - timedelta(days=180)
        if row.sc_daily < today:
            scream_time = round(datetime.timestamp(row.sc_daily))
            if row.sc_daily > yesterday:
                await interaction.followup.send(
                    f"You do not need to save your streak, scream to continue it",
                    ephemeral=True,
                )
                return
            if row.sc_daily < two_days_ago:
                await interaction.followup.send(
                    f"Your streak is too old to save (last scream was <t:{scream_time}:R>.), scream to start a new one",
                    ephemeral=True,
                )
                return
            if row.sc_streak_keeper > six_months_ago:
                save_time = round(datetime.timestamp(row.sc_streak_keeper))
                await interaction.followup.send(
                    f"You can only save your streak once every 6 months (lasted saved <t:{save_time}:R>), scream to continue it",
                    ephemeral=True,
                )
                return
            if row.sc_streak < 30:
                await interaction.followup.send(
                    f"Your streak is too short to save, scream to start a new one",
                    ephemeral=True,
                )
                return
            if confirm == "Check":
                await interaction.followup.send(
                    f"Your streak is {row.sc_streak} days long, you can save it by sacrificing 30 days of your previous streak.\nYour last scream was <t:{scream_time}:R>.",
                    ephemeral=True,
                )
                return
            async with self.bot.session as session:
                row.sc_streak_keeper = today
                row.sc_streak -= 30
                session.add(row)
                await session.commit()
            await interaction.followup.send(
                f"Your streak has been saved, you lost 30 days but kept the streak.",
                ephemeral=True,
                embed=await self.get_statistics(user.id, user.display_name, user.display_avatar),
            )

    @stats_group.command(name="override", description="Override a users existing stats.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def override(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        total: Optional[int] = None,
        streak: Optional[int] = None,
        best_streak: Optional[int] = None,
        set_daily_today: bool = False,
    ):
        await interaction.response.defer(ephemeral=True)

        async with self.bot.session as session:
            row = await session.get(Screams, user.id)
            if row is None:
                await interaction.followup.send(f"{user.display_name} has no stats to override.", ephemeral=True)
                return
            if total is not None:
                row.sc_total = total
            if streak is not None:
                row.sc_streak = streak
            if best_streak is not None:
                row.sc_best_streak = best_streak
            if set_daily_today:
                row.sc_daily = now_tz()
            session.add(row)
            await session.commit()
        await interaction.followup.send(f"Updated {user.display_name}'s stats.", ephemeral=True)


async def setup(bot):
    stats = statistics(bot)
    await stats._init()
    await bot.add_cog(stats)


async def teardown(bot):
    pass


async def destroy(bot):
    bot.modules.pop(cog_name, None)
    await teardown(bot)
