# reminder_commands.py

## TODO TODO IF CHANGING ALL ACTIVE REMINDERS WILL CONTINUE

### IMPORTS ###
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice

import asyncio
from datetime import datetime, timedelta
from sys import path

path.append("..") # Adds higher directory to python modules path.
from roles import elevated_roles


class reminders(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.reminders = []

    ### COMMANDS ###
    @commands.hybrid_command(
        name="reminder",
        aliases=['rm'],
        brief='Sets a one off reminder',
        description="Reminds you of something.",
        with_app_command = True)
    @app_commands.describe(days="Days.", hours="Hours.", minutes="Minutes.", seconds="Seconds.", message="Your reminder message.")
    @app_commands.choices(
        hours=[Choice(name=str(i), value=i) for i in range(0, 25)],
        minutes=[Choice(name=str(i), value=i) for i in range(0, 56, 5)],
        seconds=[Choice(name=str(i), value=i) for i in range(0, 56, 5)])
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def remindMe(self, ctx, days : int, hours : int, minutes: int, seconds: int, message :str):
        self.logger.info(f"{ctx.author.name} ({ctx.author.nick}) called remindMe")

        now = round(datetime.timestamp(datetime.now()))
        delta = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

        remind_in = round(datetime.timestamp(delta))

        await ctx.reply(f"Your reminder will be sent <t:{remind_in}:R>.", ephemeral = True)

        msg = f'{ctx.author.mention}, this is your reminder, Reqested <t:{now}:T> <t:{now}:d>'
        msg += f'\nYou wanted to say: {message}'

        record = (ctx.author.display_name, delta.strftime("%m/%d/%Y, %H:%M:%S"), message)

        self.reminders.append(record)

        amount = seconds + minutes * 60 + hours * 60 * 60 + days * 24 * 60 * 60
        await asyncio.sleep(amount)

        self.reminders.remove(record)

        await ctx.send(msg, ephemeral = True)

    @commands.hybrid_command(
        name="allreminders",
        brief='See active reminders',
        with_app_command = True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    @commands.has_any_role(*elevated_roles)
    async def allReminders(self, ctx):
        self.logger.info(f"{ctx.author.name} ({ctx.author.nick}) called reminders")

        if self.reminders:
            msg = "The following reminders are set:\n"
            msg += '\n'.join([
                "" + author + " wants to say: '" + message + "' at " + time
                for author, time, message in self.reminders
            ])
        else:
            msg = "No reminders are set"

        await ctx.reply(msg, ephemeral = True)


async def setup(bot):
    await bot.add_cog(reminders(bot))


async def teardown(bot):
    pass