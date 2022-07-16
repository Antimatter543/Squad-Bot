# reminder_commands.py

## TODO TODO IF CHANGING ALL ACTIVE REMINDERS WILL CONTINUE

### IMPORTS ###
import discord
from discord.ext import commands

import asyncio
import logging

from sys import path
path.append("..") # Adds higher directory to python modules path.
from roles import admin_roles, elevated_roles


class reminder_commands(commands.Cog):

    def __init__(self,client):
        self.client = client
    ### COMMANDS ###
    @commands.command(
        aliases=['rm'],
        brief='Sets a one off reminder',
        description='Sets a reminder given the amount of time'
        )
    async def remindMe(self, ctx, days : int, hours : int, minute: int, seconds: int, *, message=None):
        logging.info(f"<@{ctx.author.id}> called remindMe")
        await ctx.send(f'<@{ctx.author.id}>, reminder scheduled for {days} day(s), {hours} hour(s), {minute} minute(s) and {seconds} second(s)')
        amount = seconds + minute * 60 + hours * 60 * 60 + days * 24 * 60 * 60
        await asyncio.sleep(amount)
        await ctx.send(f'{ctx.author.mention}, this is your reminder, it has been {days} day(s), {hours} hour(s), {minute} minute(s) and {seconds} second(s) since the request')
        if message is not None:
            await ctx.send(f'you wanted to say: {message}')

def setup(client):
    client.add_cog(reminder_commands(client))

def teardown(client):
    pass