# general_commands.py

### IMPORTS ###
import discord
from discord.ext import commands

from random import choice, randint
import logging

from sys import path
path.append("..") # Adds higher directory to python modules path.
from roles import admin_roles, elevated_roles


class general(commands.Cog):

    def __init__(self, client):
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
        aliases=['8ball', 'predictions'],
        brief='Shake a make 8 ball',
        description='Get a fortune from the magic 8 ball'
        )
    async def magic_ball(self, ctx):
        logging.info(f"<@{ctx.author.id}> called magic_ball")
        options = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        await ctx.send(options[randint(0,len(options)-1)])

    @commands.command(
        aliases=['6roll', '6Roll', '6ROLL', 'Dice', 'dice'],
        brief='Roll a dice',
        description='Returns a random number between 1 and 6'
        )
    async def roll_dice(self, ctx):
        logging.info(f"<@{ctx.author.id}> called roll_dice")
        await ctx.send(f'Rolled a dice, it was a {randint(1,6)}!')

    @commands.command(
        aliases=['boolean'],
        brief='Returns yes or no',
        description='Returns yes or no randomly'
        )
    async def consent(self, ctx):
        logging.info(f"<@{ctx.author.id}> called consent")
        await ctx.send(f'{"Yes" if randint(0,1) == 1 else "No"}!')

    @commands.command(
        aliases=[''],
        brief='[Redacted]',
        description='[Redacted]'
        )
    async def sex(self, ctx):
        logging.info(f"<@{ctx.author.id}> called sex")
        options = [
            'I am an artificial being and can not satisfy you in this way.',
            'https://i.kym-cdn.com/entries/icons/original/000/033/758/Screen_Shot_2020-04-28_at_12.21.48_PM.png',
            'Nah, I mostly just lie there.',
            'With a human being? No. With myself? Most definitely.',
            "uWu"
        ]
        num = randint(0,100)
        if num < 30:
            await ctx.send(options[0])
        elif num < 60:
            await ctx.send(options[1])
        elif num < 80:
            await ctx.send(options[2])
        elif num < 90:
            await ctx.send(options[3])
        else:
            await ctx.send(options[4])


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
        if isinstance(error, commands.MissingRequiredArgument):
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


async def setup(bot):
    await bot.add_cog(general(bot))


async def teardown(bot):
    pass