# general_commands.py

### IMPORTS ###
import discord
from discord.ext import commands
from discord import app_commands

from datetime import datetime, timedelta
import pytz

from sys import path

import re
from random import randint

path.append("..") # Adds higher directory to python modules path.
from roles import elevated_roles

channel_id = [910694743728619540,997671564462002206]

class statistics(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger

    ### Listener ###
    @commands.Cog.listener()
    async def on_message(self, message):
        # don't respond to bots
        if message.author.bot:
            return

        if message.channel.id in channel_id:
            msg = message.content
            aid = message.author.id
            try:
                regexp = re.compile(r'[aA][arRgGAhH]{' + re.escape(str(randint(3,10))) + r',}')
                if regexp.search(msg):
                    async with self.bot.db.acquire() as connection:
                        # Open a transaction.
                        async with connection.transaction():
                            newDay = False
                            query = "SELECT * FROM dc_screams WHERE user_id = $1;"
                            row = await connection.fetchrow(query, aid)
                            if row is None:
                                # add and update ref
                                await connection.execute("INSERT INTO dc_screams VALUES($1, 0, 0, 0, $2)", aid, datetime(1970,1,1))
                                row = await connection.fetchrow(query, aid)
                            query = "UPDATE dc_screams\nSET\n"
                            query += f"sc_total = {row['sc_total']+1}"


                            now = datetime.now(pytz.timezone('Australia/Brisbane'))
                            today = datetime.now(pytz.timezone('Australia/Brisbane'))  \
                                .replace(hour=0, minute=0, second=0, microsecond=0) \
                                .astimezone(pytz.utc)
                            if row['sc_daily'] < today:
                                newDay = True
                                yesterday = today - timedelta(days=1)
                                if row['sc_daily'] < yesterday:
                                    streak = 0
                                else:
                                    streak = row['sc_streak']

                                streak += 1
                                query += f",\nsc_daily = $2"
                                query += f",\nsc_streak = {streak}"
                                if streak > row['sc_best_streak']:
                                    query += f",\nsc_best_streak = {streak}\n"

                            query += "\nWHERE user_id = $1;"

                            if newDay:
                                await connection.execute(query, aid, now)
                            else:
                                await connection.execute(query, aid)

                            if newDay:
                                await message.channel.send(f'Congrats <@{aid}> on your first scream of the day.\nYour current streak is: {streak}.')
            except Exception as e:
                self.logger.info(e)

    ### COMMANDS ###
    @commands.hybrid_command(
        name="stats",
        brief='Statistics of screams into the void',
        description='Gives details on the number of times people have screamed into the void',
        with_app_command = True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def statistics(self, ctx):
        self.logger.info(f"{ctx.author.name} ({ctx.author.nick}) called statistics")
        query = "SELECT * FROM dc_screams WHERE user_id = $1;"
        row = await self.bot.db.fetchrow(query, ctx.author.id)
        if row is not None:
            msg = f'{ctx.author.mention}, here are your statistics\n'
            msg += f"Total number of screams: {row['sc_total']}\n"
            msg += f"Number of consecutive days: {row['sc_streak']}\n"
            msg += f"Best streak: {row['sc_best_streak']}"
            await ctx.reply(msg, ephemeral = True, delete_after=120, mention_author=False)
        else:
            await ctx.reply(f"{ctx.author.mention}, you have not done any screaming yet.\n", ephemeral = True, delete_after=120, mention_author=False)

    async def get_user(self, aid):
        try:
            user = await self.bot.fetch_user(aid)
            user = "[Unknown]" if user is None else user
        except:
            user = "[Unknown]"
        return user

    @commands.hybrid_command(
        name="leaderboard",
        aliases=['screamtop','top'],
        brief='Statistics of best screamers into the void',
        description='Gives details on the number of times people have screamed into the void',
        with_app_command = True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def leaderboard(self, ctx):
        self.logger.info(f"{ctx.author.name} ({ctx.author.nick}) called leaderboard")

        top = 5
        query = f'select s.* from\n'
        query += f'(select user_id, sc_total, rank() OVER (order by sc_total desc) as rank from dc_screams) s\n'
        query += f'where rank <= {top}'
        bestTotal = await self.bot.db.fetch(query)

        query = f'select s.* from\n'
        query += f'(select user_id, sc_streak, rank() OVER (order by sc_streak desc) as rank from dc_screams) s\n'
        query += f'where rank <= {top}'
        bestStreak = await self.bot.db.fetch(query)

        query = f'select s.* from\n'
        query += f'(select user_id, sc_best_streak, rank() OVER (order by sc_best_streak desc) as rank from dc_screams) s\n'
        query += f'where rank <= {top}'
        bestStreakHistorical = await self.bot.db.fetch(query)

        message = " ---{ LEADERBOARD }---\n"
        now = round(datetime.timestamp(datetime.now()))
        msg = await ctx.reply(message + f"Loading... since <t:{now}:R>", ephemeral = True, mention_author=False)

        message += "-> Total Number of times screamed\n"
        for i in range(len(bestTotal)):
            username = await self.get_user(bestTotal[i]['user_id'])
            message += f"---> {bestTotal[i]['rank']}: {username} with {bestTotal[i]['sc_total']} screams.\n"
        for i in range(len(bestTotal),top):
            message += f"---> {i+1}: This could be you!\n"

        message += "-> Best active daily streak\n"
        for i in range(len(bestStreak)):
            username = await self.get_user(bestStreak[i]['user_id'])
            message += f"---> {bestStreak[i]['rank']}: {username} with {bestStreak[i]['sc_streak']} days.\n"
        for i in range(len(bestStreak),top):
            message += f"---> {i+1}: This could be you!\n"

        message += "-> Best historical daily streak\n"
        for i in range(len(bestStreakHistorical)):
            username = await self.get_user(bestStreakHistorical[i]['user_id'])
            message += f"---> {bestStreakHistorical[i]['rank']}: {username} with {bestStreakHistorical[i]['sc_best_streak']} days.\n"
        for i in range(len(bestStreakHistorical),top):
            message += f"---> {i+1}: This could be you!\n"

        await msg.edit(content=message)

async def setup(bot):
    await bot.add_cog(statistics(bot))


async def teardown(bot):
    pass