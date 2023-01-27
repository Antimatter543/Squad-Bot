# statistics.py

import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime, timedelta
import pytz

import re
from random import randint


channel_id = [910694743728619540, 997671564462002206]


class statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log

    # Listener
    @commands.Cog.listener()
    async def on_message(self, message):
        # don't respond to bots
        if message.author.bot:
            return

        if message.channel.id in channel_id:
            msg = message.content
            aid = message.author.id
            try:
                regexp = re.compile(r"[aA][arRgGAhH]{" + re.escape(str(randint(3, 10))) + r",}")
                regexp2 = re.compile(r":scream1:")
                if regexp.search(msg) or regexp2.search(msg):
                    async with self.bot.db.acquire() as connection:
                        # Open a transaction.
                        async with connection.transaction():
                            newDay = False
                            query = "SELECT * FROM dc_screams WHERE user_id = $1;"
                            row = await connection.fetchrow(query, aid)
                            if row is None:
                                # add and update ref
                                await connection.execute(
                                    "INSERT INTO dc_screams VALUES($1, 0, 0, 0, $2)", aid, datetime(1970, 1, 1)
                                )
                                row = await connection.fetchrow(query, aid)
                            query = "UPDATE dc_screams\nSET\n"
                            query += f"sc_total = {row['sc_total']+1}"

                            now = datetime.now(pytz.timezone("Australia/Brisbane"))
                            today = (
                                datetime.now(pytz.timezone("Australia/Brisbane"))
                                .replace(hour=0, minute=0, second=0, microsecond=0)
                                .astimezone(pytz.utc)
                            )
                            if row["sc_daily"] < today and regexp.search(msg):
                                newDay = True
                                yesterday = today - timedelta(days=1)
                                if row["sc_daily"] < yesterday:
                                    streak = 0
                                else:
                                    streak = row["sc_streak"]

                                streak += 1
                                query += f",\nsc_daily = $2"
                                query += f",\nsc_streak = {streak}"
                                if streak > row["sc_best_streak"]:
                                    query += f",\nsc_best_streak = {streak}\n"

                            query += "\nWHERE user_id = $1;"

                            if newDay:
                                await connection.execute(query, aid, now)
                            else:
                                await connection.execute(query, aid)

                            if newDay:
                                await message.channel.send(
                                    f"Congrats <@{aid}> on your first scream of the day.\nYour current streak is: {streak}."
                                )
                                if streak == 100:
                                    await message.channel.send(
                                        "https://i.guim.co.uk/img/media/8a840f693b91fe67d42555b24c6334e9298f4680/251_1497_2178_1306/master/2178.jpg?width=1200&height=900&quality=85&auto=format&fit=crop&s=9ff658ed0e9b905fa583c592cc2342f5"
                                    )
                                    await message.channel.send("Congrats on reaching 100!")
            except Exception as e:
                self.log.info(e)

    # Commands
    @commands.hybrid_command(
        name="stats",
        brief="Statistics of screams into the void",
        description="Gives details on the number of times people have screamed into the void",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def statistics(self, ctx):
        query = "SELECT * FROM dc_screams WHERE user_id = $1;"
        row = await self.bot.db.fetchrow(query, ctx.author.id)
        if row is not None:
            msg = f"{ctx.author.mention}, here are your statistics\n"
            msg += f"Total number of screams: {row['sc_total']}\n"
            msg += f"Number of consecutive days: {row['sc_streak']}\n"
            msg += f"Best streak: {row['sc_best_streak']}"
            await ctx.reply(msg, ephemeral=True, delete_after=120, mention_author=False)
        else:
            await ctx.reply(
                f"{ctx.author.mention}, you have not done any screaming yet.\n",
                ephemeral=True,
                delete_after=120,
                mention_author=False,
            )

    @commands.hybrid_command(
        name="didiscream",
        brief="Check if this user has screamed yet today",
        description="Gives details on the number of times people have screamed into the void",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def didiscream(self, ctx, user=None):
        if user is None:
            user = ctx.author.id
        else:
            user = user.strip('<').strip('@').strip('>')
            if not user.isdigit():
                await ctx.reply("Please select a user", ephemeral=True, delete_after=120, mention_author=False)
                return
            user = int(user)

        query = "SELECT * FROM dc_screams WHERE user_id = $1;"
        row = await self.bot.db.fetchrow(query, user)
        if row is not None:
            today = (
                datetime.now(pytz.timezone("Australia/Brisbane"))
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .astimezone(pytz.utc)
            )
            self.bot.log.info(row["sc_daily"])
            if row["sc_daily"] < today:
                msg = "You have not screamed yet today."
            else:
                msg = "You have screamed today."
            await ctx.reply(msg, ephemeral=True, delete_after=120, mention_author=False)
        else:
            await ctx.reply(
                f"User does not exist or has not done any screaming yet.\n",
                ephemeral=True,
                delete_after=120,
                mention_author=False,
            )

    async def get_user(self, aid):
        try:
            user = await self.bot.fetch_user(aid)
            user = "[Unknown]" if user is None else user
        except Exception:
            user = "[Unknown]"
        return user

    @commands.hybrid_command(
        name="leaderboard",
        aliases=["screamtop", "top"],
        brief="Statistics of best screamers into the void",
        description="Gives details on the number of times people have screamed into the void",
        with_app_command=True,
    )
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def leaderboard(self, ctx):
        top = 5
        query = f"select s.* from\n"
        query += f"(select user_id, sc_total, rank() OVER (order by sc_total desc) as rank from dc_screams where user_id != 328794426560217088) s\n"
        query += f"where rank <= {top}"
        bestTotal = await self.bot.db.fetch(query)

        query = f"select s.* from\n"
        query += f"(select user_id, sc_streak, rank() OVER (order by sc_streak desc) as rank from dc_screams where user_id != 328794426560217088) s\n"
        query += f"where rank <= {top}"
        bestStreak = await self.bot.db.fetch(query)

        query = f"select s.* from\n"
        query += f"(select user_id, sc_best_streak, rank() OVER (order by sc_best_streak desc) as rank from dc_screams where user_id != 328794426560217088) s\n"
        query += f"where rank <= {top}"
        bestStreakHistorical = await self.bot.db.fetch(query)

        message = " ---{ LEADERBOARD }---\n"
        now = round(datetime.timestamp(datetime.now()))
        msg = await ctx.reply(message + f"Loading... since <t:{now}:R>", ephemeral=True, mention_author=False)

        message += "-> Total Number of times screamed\n"
        for i in range(len(bestTotal)):
            username = await self.get_user(bestTotal[i]["user_id"])
            message += f"---> {bestTotal[i]['rank']}: {username} with {bestTotal[i]['sc_total']} screams.\n"
        for i in range(len(bestTotal), top):
            message += f"---> {i+1}: This could be you!\n"

        message += "-> Best active daily streak\n"
        for i in range(len(bestStreak)):
            username = await self.get_user(bestStreak[i]["user_id"])
            message += f"---> {bestStreak[i]['rank']}: {username} with {bestStreak[i]['sc_streak']} days.\n"
        for i in range(len(bestStreak), top):
            message += f"---> {i+1}: This could be you!\n"

        message += "-> Best historical daily streak\n"
        for i in range(len(bestStreakHistorical)):
            username = await self.get_user(bestStreakHistorical[i]["user_id"])
            message += f"---> {bestStreakHistorical[i]['rank']}: {username} with {bestStreakHistorical[i]['sc_best_streak']} days.\n"
        for i in range(len(bestStreakHistorical), top):
            message += f"---> {i+1}: This could be you!\n"

        await msg.edit(content=message)


async def setup(bot):
    await bot.add_cog(statistics(bot))


async def teardown(bot):
    pass
