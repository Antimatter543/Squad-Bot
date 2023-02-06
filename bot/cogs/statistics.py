# statistics.py

import re
from datetime import datetime, timedelta
from random import randint
from typing import Optional

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from bot.lib.utils import now_tz

# UQCSC, TEST
channel_id = [910694743728619540, 997671564462002206]


class UnkownUser:
    def __init__(self) -> None:
        self.display_name = "[Unknown]"

    def __str__(self) -> str:
        return self.display_name


class statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
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
        query = (
            "CREATE TABLE IF NOT EXISTS dc_screams (\n"
            "user_id BIGINT PRIMARY KEY,\n"
            "sc_total INT,\n"
            "sc_streak INT,\n"
            "sc_best_streak INT,\n"
            "sc_daily TIMESTAMP WITH TIME ZONE\n"
            ");"
        )
        async with self.bot.db.acquire() as connection:
            await connection.execute(query)

    @property
    def today(self):
        return now_tz().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(pytz.utc)

    # Listener
    @commands.Cog.listener()
    @commands.bot_has_permissions(manage_roles=True)
    async def on_message(self, message):
        # don't respond to bots
        if message.author.bot:
            return

        if message.channel.id in channel_id:
            msg = message.content
            author = message.author
            aid = author.id
            guild = author.guild
            try:
                regexp = re.compile(r"[aA][arRgGAhH]{" + re.escape(str(randint(5, 15))) + r",}")
                regexp2 = re.compile(r":scream1:")
                if regexp.search(msg) or regexp2.search(msg):
                    async with self.bot.db.acquire() as connection:
                        # Open a transaction.
                        async with connection.transaction():
                            # see if user has screamed
                            query = "SELECT * FROM dc_screams WHERE user_id = $1;"
                            row = await connection.fetchrow(query, aid)
                            if row is None:
                                # add and update ref
                                await connection.execute(
                                    "INSERT INTO dc_screams VALUES($1, 0, 0, 0, $2)", aid, datetime(1970, 1, 1)
                                )
                                row = await connection.fetchrow(query, aid)

                            # Start update
                            query = "UPDATE dc_screams\nSET\n"
                            query += f"sc_total = {row['sc_total']+1}"

                            now = now_tz()
                            today = self.today

                            # check if new day
                            newDay = False
                            streak = 0
                            if row["sc_daily"] < today and regexp.search(msg):
                                newDay = True
                                yesterday = today - timedelta(days=1)
                                if row["sc_daily"] > yesterday:
                                    streak = row["sc_streak"]

                                streak += 1
                                query += f",\nsc_daily = $2"
                                query += f",\nsc_streak = {streak}"
                                if streak > row["sc_best_streak"]:
                                    query += f",\nsc_best_streak = {streak}\n"

                            query += "\nWHERE user_id = $1;"

                            if newDay:
                                await connection.execute(query, aid, now)

                                await message.channel.send(
                                    f"Congrats {author.mention} on your first scream of the day.\nYour current streak is: {streak}."
                                )
                                if streak % 100 == 0:
                                    await message.channel.send(
                                        "https://i.guim.co.uk/img/media/8a840f693b91fe67d42555b24c6334e9298f4680/251_1497_2178_1306/master/2178.jpg?width=1200&height=900&quality=85&auto=format&fit=crop&s=9ff658ed0e9b905fa583c592cc2342f5"
                                    )
                                    await message.channel.send(f"Congrats on reaching {streak}!")
                                if streak == self.bot.config.get("STAT_SC_MINOR", 100):
                                    role = discord.utils.get(guild.roles, name="Void Veteran")
                                    await author.add_roles(role)
                                if streak == self.bot.config.get("STAT_SC_MAJOR", 250):
                                    role = discord.utils.get(guild.roles, name="Legends of the Void")
                                    await author.add_roles(role)
                            else:
                                await connection.execute(query, aid)
            except Exception as e:
                self.log.info(e)

    async def get_statistics(self, uid, name, avatar) -> discord.Embed:
        query = "SELECT * FROM dc_screams WHERE user_id = $1;"
        async with self.bot.db.acquire() as connection:
            row = await connection.fetchrow(query, uid)
        embed = discord.Embed(title="Scream Statistics", description=f"{name}, here are you statistics.")
        embed.set_author(name=f"{name}")
        embed.set_thumbnail(url=f"{avatar}")
        if row is not None:
            embed.add_field(name="Total Screams", value=f"{row['sc_total']}")
            embed.add_field(name="Scream Streak", value=f"{row['sc_streak']}")
            embed.add_field(name="Best Scream Streak", value=f"{row['sc_best_streak']}")
        else:
            embed.add_field(name="", value="No screams as of yet.")
        return embed

    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def statistics_menu(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        uid = user.id
        name = user.display_name
        avatar = user.display_avatar
        embed = await self.get_statistics(uid, name, avatar)
        msg = await interaction.followup.send(embed=embed, ephemeral=True, wait=True)
        await msg.delete(delay=120)

    # Commands
    @commands.hybrid_command(
        name="stats",
        brief="Statistics of screams into the void",
        description="Gives details on the number of times people have screamed into the void",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def statistics(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        await ctx.defer(ephemeral=True)
        if user is None:
            user = ctx.author

        uid = user.id
        name = user.display_name
        avatar = user.display_avatar
        embed = await self.get_statistics(uid, name, avatar)
        await ctx.reply(embed=embed, ephemeral=True, delete_after=120, mention_author=False)

    async def get_has_screamed(self, uid, start="", name="User") -> str:
        query = "SELECT * FROM dc_screams WHERE user_id = $1;"
        async with self.bot.db.acquire() as connection:
            row = await connection.fetchrow(query, uid)
        if row is not None:
            self.bot.log.info(row["sc_daily"])
            if row["sc_daily"] < self.today:
                msg = start + "have not screamed yet today."
            else:
                msg = start + "have screamed today."
        else:
            msg = f"{name} has not done any screaming yet."
        return msg

    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
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

    @commands.hybrid_command(
        name="didiscream",
        brief="Check if this user has screamed yet today",
        description="Check if this user has screamed yet today",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def didiscream(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        await ctx.defer(ephemeral=True)
        if user is None:
            user = ctx.author
            start = "You "
        else:
            start = "They "

        uid = user.id
        msg = await self.get_has_screamed(uid, start)
        await ctx.reply(msg, ephemeral=True, delete_after=120, mention_author=False)

    async def get_user(self, aid):
        try:
            user = await self.bot.fetch_user(aid)
            user = UnkownUser() if user is None else user
        except Exception:
            user = UnkownUser()
        return user

    @commands.hybrid_command(
        name="leaderboard",
        aliases=["screamtop", "top"],
        brief="Statistics of best screamers into the void",
        description="Gives details on the number of times people have screamed into the void",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516), discord.Object(id=676253010053300234))
    async def leaderboard(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True)
        now = round(datetime.timestamp(now_tz()))

        header = "---{ Scream Leaderboard }---"

        embed = discord.Embed(title=f"{header}", description=f"The top screamers", color=discord.Color.darker_grey())
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1043839508887634010.webp?size=96&quality=lossless")

        msg = await ctx.reply(f"{header}\nLoading... since <t:{now}:R>", ephemeral=True, mention_author=False)

        top = 5
        queries = [
            (
                "SELECT s.* FROM\n"
                f"(SELECT user_id, {table}, rank() OVER (order by {table} desc) as rank FROM dc_screams) s"
                f" WHERE s.rank <= {top};"
            )
            for table in ["sc_total", "sc_streak", "sc_best_streak"]
        ]

        async with self.bot.db.acquire() as connection:
            bestTotal = await connection.fetch(queries[0])

            bestStreak = await connection.fetch(queries[1])

            bestStreakHistorical = await connection.fetch(queries[2])

        emoji = {1: ":one:", 2: ":two:", 3: ":three:", 4: ":four:", 5: ":five:"}

        message = ""
        for i in range(len(bestTotal)):
            user = await self.get_user(bestTotal[i]["user_id"])
            message += (
                f"{emoji[bestTotal[i]['rank']]}\u27F6 {user.display_name} with {bestTotal[i]['sc_total']} screams.\n"
            )
        for i in range(len(bestTotal), top):
            message += f"{emoji[i+1]}\u27F6 This could be you!\n"
        embed.add_field(name="__Total Number of times screamed__", value=f"{message}", inline=False)

        message = ""
        for i in range(len(bestStreak)):
            user = await self.get_user(bestStreak[i]["user_id"])
            message += (
                f"{emoji[bestStreak[i]['rank']]}\u27F6 {user.display_name} with {bestStreak[i]['sc_streak']} days.\n"
            )
        for i in range(len(bestStreak), top):
            message += f"{emoji[i+1]}\u27F6 This could be you!\n"
        embed.add_field(name="__Best active daily streak__", value=f"{message}", inline=False)

        message = ""
        for i in range(len(bestStreakHistorical)):
            user = await self.get_user(bestStreakHistorical[i]["user_id"])
            message += f"{emoji[bestStreakHistorical[i]['rank']]}\u27F6 {user.display_name} with {bestStreakHistorical[i]['sc_best_streak']} days.\n"
        for i in range(len(bestStreakHistorical), top):
            message += f"{emoji[i+1]}\u27F6 This could be you!\n"
        embed.add_field(name="__Best historical daily streak__", value=f"{message}", inline=False)

        await msg.edit(content="", embed=embed)


async def setup(bot):
    stats = statistics(bot)
    await stats._init()
    await bot.add_cog(stats)


async def teardown(bot):
    pass
