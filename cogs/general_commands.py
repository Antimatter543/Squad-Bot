# general_commands.py

### IMPORTS ###
import discord
from discord.ext import commands

from random import choice, randint
import logging

from sys import path
path.append("..") # Adds higher directory to python modules path.
from roles import admin_roles, elevated_roles


class general_commands(commands.Cog):

    def __init__(self,client):
        self.client = client

    ### COMMANDS ###
    @commands.command(
        aliases=['p'],
        brief='Pong!, latency test',
        description='Sends Pong!, followed by the result of a latecny test'
        )
    async def ping(self, ctx):
        logging.info(f"<@{ctx.author.id}> called ping")
        await ctx.send(f'Pong! {round(self.client.latency * 1000)}ms')

    @commands.command(
        aliases=['6roll','6Roll','6ROLL','Dice','dice'],
        brief='Roll a dice',
        description='Returns a random number between 1 and 6'
        )
    async def roll_dice(self, ctx):
        logging.info(f"<@{ctx.author.id}> called roll_dice")
        await ctx.send(f'Rolled a dice, it was a {randint(0,6)}!')

    @commands.command(aliases=['d','choose','c'],
        brief='Chooses between a list of items',
        description='Returns a random value from a list of items given following the command (seperated by spaces)'
        )
    async def decide(self, ctx, *, options):
        logging.info(f"<@{ctx.author.id}> called decide")
        options = options.split(' ')
        await ctx.send(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')

    @decide.error
    async def decide_error(self, ctx, error):
        if isinstance(error,commands.MissingRequiredArgument):
            await ctx.send('Please specify a list of items to choose from (seperated by spaces)')
        else:
            await ctx.send(f'An error occured, {error}')

    @commands.command(
        brief='Clears a number of messages',
        description='Clears a number of previous messages from a channel\nRequires an elevated role.'
        )
    @commands.has_any_role(*elevated_roles)
    async def clear(self, ctx, amount=5):
        logging.warning(f"<@{ctx.author.id}> called clear")
        await ctx.channel.purge(limit=(amount+1))


def setup(client):
    client.add_cog(general_commands(client))

def teardown(client):
    pass