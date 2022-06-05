# general_commands.py

### IMPORTS ###
import discord
from discord.ext import commands

from random import choice, randint

# TODO update in all files
allowed_roles = ['OG Squad']
admin_roles = ['Developer']
elevated_roles = ['Mody Boi']
elevated_roles.extend(admin_roles)


class general_commands(commands.Cog):

    def __init__(self, client):
        self.client = client

    ### COMMANDS ###
    @commands.command(
        aliases=['p'],
        brief='Pong!, latency test',
        description='Sends Pong!, followed by the result of a latecny test\nRequires a role of "OG Squad" or higher'
    )
    @commands.has_any_role(*allowed_roles)
    async def ping(self, ctx):
        await ctx.send(f'Pong! {round(self.client.latency * 1000)}ms')

    @commands.command(
        aliases=['6roll', '6Roll', '6ROLL', 'Dice', 'dice'],
        brief='Roll a dice',
        description='Returns a random number between 1 and 6\nRequires a role of "OG Squad" or higher'
    )
    @commands.has_any_role(*allowed_roles)
    async def roll_dice(self, ctx):
        await ctx.send(f'Rolled a dice, it was a {randint(0,6)}!')

    @commands.command(aliases=['d', 'choose', 'c'],
                      brief='Chooses between a list of items',
                      description='Returns a random value from a list of items given following the command (seperated by spaces)\nRequires a role of "OG Squad" or higher'
                      )
    @commands.has_any_role(*allowed_roles)
    async def decide(self, ctx, *, options):
        options = options.split(' ')
        await ctx.send(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')

    @decide.error
    async def decide_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please specify a list of items to choose from (seperated by spaces)')
        else:
            await ctx.send(f'An error occured, {error}')

    @commands.command(
        brief='Clears a number of messages',
        description='Clears a number of previous messages from a channel\nRequires a role of "Mody Boi" or higher'
    )
    @commands.has_any_role(*elevated_roles)
    async def clear(self, ctx, amount=5):
        await ctx.channel.purge(limit=(amount+1))


def setup(client):
    client.add_cog(general_commands(client))


def teardown(client):
    pass
