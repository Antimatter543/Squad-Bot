# general_commands.py

### IMPORTS ###
import discord
from discord import app_commands
from discord.ext import commands

from random import choice, randint
import logging

from sys import path
path.append("..") # Adds higher directory to python modules path.
from roles import elevated_roles


class general(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.sLog = {}

    ### COMMANDS ###
    @commands.hybrid_command(
        name="ping",
        aliases=['p'],
        brief='Pong!, latency test',
        description='Sends Pong!, followed by the result of a latecny test',
        with_app_command = True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def ping(self, ctx):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called ping")
        await ctx.reply(f'Pong! {round(self.bot.latency * 1000)}ms', ephemeral = True)


    @commands.hybrid_command(
        name="fortune",
        aliases=['8ball', 'predictions', 'shake', "magic_ball"],
        brief='Shake a magic 8 ball',
        description='Get a fortune from the magic 8 ball',
        with_app_command = True)
    @app_commands.describe(message="What do you wish to ask?")
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def magic_ball(self, ctx, message=""):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called magic_ball")
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
        await ctx.reply(options[randint(0,len(options)-1)])

    @commands.hybrid_command(
        name="6roll",
        aliases=['roll_dice', 'dice'],
        brief='Roll a dice',
        description='Returns a random number between 1 and 6',
        with_app_command = True)
    @app_commands.describe(sides="Number of sides.")
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def roll_dice(self, ctx, sides:int = 6):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called roll_dice")
        await ctx.send(f'Rolled a dice, it was a {randint(1,sides)}!')

    @commands.hybrid_command(
        name="hug",
        aliases=['love'],
        brief='',
        description='',
        with_app_command = True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def hug(self, ctx):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called hug")
        await ctx.reply(f':hugging:')

    @commands.command(
        aliases=['sex2', 'biggus dickus','cock','cum','cumsum','dick','balls'],
        hidden=True
        )
    async def sex(self, ctx):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called sex")
        if ctx.author.id not in self.sLog:
            self.sLog[ctx.author.id] = 0
        self.sLog[ctx.author.id] += 1
        if self.sLog[ctx.author.id] % 20 == 0:
            await ctx.send("https://i.redd.it/ofq6raed4ck71.jpg")
            return
        if self.sLog[ctx.author.id] % 50 == 0:
            await ctx.send("https://preview.redd.it/uvvfzj73pae71.png?auto=webp&s=2ccf99549a0f445170e15e0227404d804d8052fb")
            return
        options = [
            'I am an artificial being and can not satisfy you in this way.',
            'https://i.kym-cdn.com/entries/icons/original/000/033/758/Screen_Shot_2020-04-28_at_12.21.48_PM.png',
            'Nah, I mostly just lie there.',
            'With a human being? No. With myself? Most definitely.',
            "uWu"
        ]
        num = randint(0,100)
        if num < 20:
            await ctx.send(options[0])
        elif num < 70:
            await ctx.send(options[1])
        elif num < 80:
            await ctx.send(options[2])
        elif num < 90:
            await ctx.send(options[3])
        else:
            await ctx.send(options[4])

    @commands.command(
        name="decide",
        aliases=['d','choose','c'],
        brief='Chooses between a list of items',
        description='Returns a random value from a list of items given following the command')
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def decide(self, ctx, *options):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called decide")
        if(len(options) == 0):
            return
        await ctx.reply(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')

    @app_commands.command(
        name="decide",
        description='Returns a random value from a list of items given following the command')
    @app_commands.guilds(discord.Object(id=809997432011882516))
    async def decide_slash(self, ctx,
                           o0:str, o1:str="", o2:str="", o3:str="",
                           o4:str="", o5:str="", o6:str="", o7:str="",
                           o8:str="", o9:str=""):
        logging.info(f"{ctx.author.name} ({ctx.author.nick}) called decide")
        options = [ o0, o1, o2, o3, o4, o5, o6, o7, o8, o9]
        options = [x for x in options if x != ""]
        await ctx.reply(f'Options: [{"],[".join(options)}]\nSelected: {choice(options)}')

    @decide.error
    async def decide_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please specify a list of items to choose from (seperated by spaces)')
        else:
            await ctx.send(f'An error occured, {error}')

    @commands.hybrid_command(
        name="clear",
        brief='Clears a number of your past messages',
        description='Clears a number of previous messages from a channel',
        with_app_command = True)
    @app_commands.guilds(discord.Object(id=809997432011882516))
    @commands.has_any_role(*elevated_roles)
    async def clear(self, ctx, amount=5):
        logging.warning(f"{ctx.author.name} ({ctx.author.nick}) called clear")
        await ctx.channel.purge(limit=amount, before=ctx.message)


async def setup(bot):
    await bot.add_cog(general(bot))


async def teardown(bot):
    pass