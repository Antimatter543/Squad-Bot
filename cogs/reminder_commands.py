# reminder_commands.py

## TODO TODO IF CHANGING ALL ACTIVE REMINDERS WILL CONTINUE

### IMPORTS ###
import discord
from discord.ext import commands

import asyncio

### TODO update in all files
allowed_roles = ['OG Squad']
admin_roles = ['Developer']
elevated_roles = ['Mody Boi']
elevated_roles.extend(admin_roles)
allowed_roles.extend(elevated_roles)

class reminder_commands(commands.Cog):

    def __init__(self,client):
        self.client = client
        self.reminders = {}
    ### COMMANDS ###
    @commands.command(
        aliases=['rm'],
        brief='Sets a one off reminder',
        description='Sets a reminder given the amount of time'
        )
    @commands.has_any_role(*allowed_roles)
    async def remindMe(self, ctx, days : int, hours : int, minute: int, seconds: int, *, message=None):
        if message == None:
            await ctx.send(f'<@{ctx.author.id}>, reminder schedules for {days} day(s), {hours} hour(s), {minute} minute(s) and {seconds} second(s)') 
            amount = seconds + minute * 60 + hours * 60 * 60 + days * 24 * 60 * 60
            await asyncio.sleep(amount)
            await ctx.send(f'{ctx.author.mention}, this is your reminder, it has been {days} day(s), {hours} hour(s), {minute} minute(s) and {seconds} second(s) since the request')
        else:
            await ctx.send(f'<@{ctx.author.id}>, reminder schedules for {days} day(s), {hours} hour(s), {minute} minute(s) and {seconds} second(s)') 
            amount = seconds + minute * 60 + hours * 60 * 60 + days * 24 * 60 * 60
            await asyncio.sleep(amount)
            await ctx.send(f'{ctx.author.mention}, this is your reminder, it has been {days} day(s), {hours} hour(s), {minute} minute(s) and {seconds} second(s) since the request')
            await ctx.send(f'you wanted to say: {message}')

    @commands.command(
        brief='Admin ONLY',
        description='Sets a reoccuring reminder once a week that occurs one week from the first call'
        )
    @commands.has_any_role(*admin_roles)
    async def weekReminder(self, ctx, *, reference):
        self.reminders.update({reference : True})
        await self.client.wait_until_ready()
        while not self.client.is_closed() and self.reminders[reference]:
            await ctx.send(f'{[guild for guild in self.client.guilds if guild.id == 702830850999451658][0].get_role(706110686501273602).mention}, it\'s  Thursday mah dudes') 
            await asyncio.sleep(7*24*60*60)
            # await ctx.send(f'{reference}')
            # await asyncio.sleep(10)
        del self.reminders[reference]

    @commands.command(
        brief='Admin ONLY',
        description='Shows currently active reminders'
        )
    @commands.has_any_role(*admin_roles)
    async def activeReminders(self, ctx):
            await ctx.send(f'{self.reminders}')

    @commands.command(
        brief='Admin ONLY',
        description='disables reminder'
        )
    @commands.has_any_role(*admin_roles)
    async def disableReminders(self, ctx, item):
            await ctx.send(f'{self.reminders}')
            self.reminders[item] = False
            await ctx.send(f'updated to {self.reminders}')

def setup(client):
    client.add_cog(reminder_commands(client))

def teardown(client):
    pass